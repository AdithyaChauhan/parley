// One fake Parley user, shared by every scenario (D33). It does what the app
// does: open with a saved session, get a ticket, open the live line, ping
// every 25 s, send to its partner, send "read" for what arrives, and catch up
// by number after a gap (D21). And it times it all: send → 201, and send →
// the partner's live line.
//
// Every user runs inside the same k6 program, so they share one clock: the
// sender writes the time into the message, and the partner subtracts it.

import http from "k6/http";
import exec from "k6/execution";
import { sleep } from "k6";
import { SharedArray } from "k6/data";
import { Counter, Rate, Trend } from "k6/metrics";
import { clearInterval, clearTimeout, setInterval, setTimeout } from "k6/timers";
import { WebSocket } from "k6/websockets";

const BASE = __ENV.BASE_URL || "http://web:8080";
const LIVE = BASE.replace(/^http/, "ws") + "/api/live";
// Each user's saved refresh token, from seed.py (load0001 first). A
// SharedArray is read once and shared by every user, not copied 1,000 times.
const TOKENS = new SharedArray("sessions", () => JSON.parse(open("./sessions.json")));
// Users start 10 a second: 1,000 are ready in ~100 s. At 50 a second (D33's
// plan), the start-up burst froze the old code (see docs/load-test.md). This
// keeps the start out of the measurements, and the same as T31's "before" runs.
const START_EVERY_S = Number(__ENV.START_EVERY_S) || 0.1;

// Timings, in milliseconds.
const e2e = new Trend("e2e_latency", true); // send → the partner's live line has it
const sendTime = new Trend("send_time", true); // send → 201 (retries included)
const connectTime = new Trend("connect_time", true); // ask for a ticket → hello
const helloWait = new Trend("hello_wait", true); // line open → hello: the subscribe lock (D23) sits here
const reconnectTime = new Trend("reconnect_time", true); // line dropped → hello again

// Counts.
const sent = new Counter("msgs_sent"); // got 201 (or 200 for a resend)
const received = new Counter("msgs_received"); // partner messages seen, each one once
const caughtUp = new Counter("msgs_caught_up"); // ...that came by catch-up, not live
const late = new Counter("msgs_late"); // ...that took over 1 s
const sendFailed = new Rate("send_failed"); // send tries that didn't get 201/200
const sendBusy = new Counter("send_busy"); // ...of which a quick 503 "busy" (D34)
const sendGaveUp = new Counter("send_gave_up"); // sends still not through when the chat ended
const busyTime = new Trend("busy_time", true); // how fast a send's 503 came
const connectFailed = new Counter("connect_failed"); // no hello within 10 s, or a broken ticket reply
const connectBusy = new Counter("connect_busy"); // a ticket 503 "busy" (D34): tries again, like the app
const lineDrops = new Counter("line_drops"); // a working line that closed on us

const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
// A 503 "busy" says when to come back (D34).
const retryAfter = (reply) => Number(reply.headers["Retry-After"]) || 1;

// The k6 settings every scenario shares.
export function optionsFor(plan, extra = {}) {
  return {
    scenarios: {
      // One run of fakeUser() per user: it lasts the whole test.
      users: {
        executor: "per-vu-iterations",
        vus: plan.users,
        iterations: 1,
        maxDuration: `${plan.closeAt + 60}s`,
      },
    },
    // Not the address: otherwise every ticket and chat id would become its
    // own line in Prometheus (like route templates, D32).
    systemTags: ["scenario", "name", "method", "status", "expected_response", "error_code"],
    summaryTrendStats: ["min", "med", "p(95)", "p(99)", "max", "count"],
    ...extra,
  };
}

// plan: when things happen, in seconds after the start.
//   users                how many (pairs: 1+2, 3+4, ...)
//   group, fanout        scenario f: everyone talks in the one group seed.py made,
//                        and each message should reach fanout people (D37)
//   connectAt(i)         when user i opens its line (leave out: right after logging in)
//   chatFrom, chatUntil  when users send
//   gap(t)               seconds between one user's sends, on average, at time t
//   stage(t)             a label for the step at time t (finding the limit)
//   closeAt              when everyone hangs up
export async function fakeUser(plan) {
  const start = exec.scenario.startTime; // the same for every user
  const at = (seconds) => start + seconds * 1000; // "N s after the start", as a clock time
  const now = () => (Date.now() - start) / 1000; // seconds since the start
  const i = exec.vu.idInTest; // 1, 2, 3 ... = load0001, load0002 ...

  // 1. Open with my saved session, like a browser that's already logged in:
  // the refresh cookie buys a 15-minute access token, with no password check
  // (D16, D33). Then find my one chat (the app gets it from the chat list too).
  sleep(Math.max(0, at((i - 1) * START_EVERY_S) - Date.now()) / 1000);
  // A 503 "busy" did nothing yet, so it's safe to ask again (D34).
  const untilNotBusy = (ask) => {
    for (;;) {
      const reply = ask();
      if (reply.status !== 503) return reply;
      sleep(retryAfter(reply));
    }
  };
  const session = untilNotBusy(() =>
    http.post(`${BASE}/api/auth/refresh`, null, { cookies: { refresh_token: TOKENS[i - 1] }, tags: { name: "refresh" } }),
  );
  if (session.status !== 200) return; // counted in http_req_failed
  const auth = { headers: { Authorization: `Bearer ${session.json("access_token")}`, "Content-Type": "application/json" } };
  const myChats = untilNotBusy(() => http.get(`${BASE}/api/chats`, { ...auth, tags: { name: "chats" } })).json();
  // A pair talks in its direct chat. In a group, every other member's message
  // counts, so I need my own id (D37).
  const myChat = plan.group ? myChats.find((c) => c.kind === "group") : myChats[0];
  const chat = myChat.id;
  const partner = myChat.other_user_id;
  const me = plan.group ? untilNotBusy(() => http.get(`${BASE}/api/auth/me`, { ...auth, tags: { name: "me" } })).json("id") : null;
  const fromOthers = (m) => (plan.group ? m.sender_id !== me : m.sender_id === partner);

  let socket = null; // the working line, once it said hello
  let closing = false; // true at the end: no more reconnects
  let tries = 0; // failed connects in a row, for the backoff
  let droppedAt = 0; // when the working line dropped, for reconnect_time
  let gapFree = 0; // the highest number with no hole below it (D21)
  const seen = new Set(); // every number I have, live or by catch-up
  let readSent = 0;
  let readAt = 0; // when the last "read" went
  let readBooked = null; // a "read" waiting out its second
  let catchingUp = false;
  let catchUpAgain = false;

  // 2. The live line: ticket, open, hello. A drop reconnects like the app (D21).
  async function connect() {
    if (closing) return;
    const asked = Date.now();
    const reply = await http.asyncRequest("POST", `${BASE}/api/live/ticket`, null, { ...auth, tags: { name: "ticket" } });
    if (reply.status !== 200) {
      (reply.status === 503 ? connectBusy : connectFailed).add(1);
      return retryLater();
    }

    const ws = new WebSocket(`${LIVE}?ticket=${reply.json("ticket")}`, null, { tags: { name: "live" } });
    let opened = 0;
    let saidHello = false;
    let ended = false;
    let pingTimer = null;
    let pongTimer = null;
    // No hello within 10 s counts as a dead line, like the app.
    const noHello = setTimeout(() => ws.close(), 10_000);

    ws.onopen = () => {
      opened = Date.now();
    };
    ws.onmessage = (message) => {
      const event = JSON.parse(message.data);
      if (event.type === "hello") {
        saidHello = true;
        clearTimeout(noHello);
        tries = 0;
        socket = ws;
        connectTime.add(Date.now() - asked);
        helloWait.add(Date.now() - opened);
        if (droppedAt) {
          reconnectTime.add(Date.now() - droppedAt);
          droppedAt = 0;
        }
        // The heartbeat: a ping every 25 s, and no pong within 10 s means dead.
        pingTimer = setInterval(() => {
          ws.send(JSON.stringify({ type: "ping", data: {} }));
          pongTimer = setTimeout(() => ws.close(), 10_000);
        }, 25_000);
        // Every hello is the cue to catch up, like the app (D21).
        catchUp();
      } else if (event.type === "message.new") {
        gotMessage(event.data, "live");
      } else if (event.type === "pong") {
        clearTimeout(pongTimer);
      }
    };
    // A failed line can report both an error and a close: handle it once.
    const lineEnded = () => {
      if (ended) return;
      ended = true;
      clearTimeout(noHello);
      clearInterval(pingTimer);
      clearTimeout(pongTimer);
      if (socket === ws) socket = null;
      if (closing) return;
      if (saidHello) {
        lineDrops.add(1);
        droppedAt = Date.now();
      } else {
        connectFailed.add(1);
      }
      retryLater();
    };
    ws.onclose = lineEnded;
    ws.onerror = lineEnded;
  }

  // Wait 1, 2, 4 ... up to 30 s, plus up to 1 s at random, then a new ticket (D21).
  function retryLater() {
    if (closing) return;
    const wait = Math.min(30, 2 ** tries) + Math.random();
    tries += 1;
    setTimeout(connect, wait * 1000);
  }

  // 3. A message arrived, live or by catch-up. Each number counts once.
  function gotMessage(m, via) {
    if (seen.has(m.seq)) return;
    seen.add(m.seq);
    while (seen.has(gapFree + 1)) gapFree += 1;

    // Group notes carry no timing (D37). None are made during a run anyway.
    if (m.kind !== "system" && fromOthers(m)) {
      const { t, s } = JSON.parse(m.body);
      const took = Date.now() - t;
      const tags = s ? { via, stage: s } : { via };
      e2e.add(took, tags);
      received.add(1, tags);
      if (via === "catchup") caughtUp.add(1, tags);
      if (took > 1000) late.add(1, tags);
      // Both people have the chat open, so it's read at once (D33).
      // Scenario f can turn reads off, to measure the message fan-out alone.
      if (plan.reads !== false) sendRead();
    }
    // A number was skipped (#41, then #43): something got lost on the way.
    if (via === "live" && m.seq > gapFree) catchUp();
  }

  // "read" up to my gap-free number, at most once a second, like the app (D20):
  // a read inside the second is booked, and goes then with the highest number.
  function sendRead() {
    if (readBooked) return;
    const waitMs = readAt + 1000 - Date.now();
    if (waitMs > 0) {
      readBooked = setTimeout(() => {
        readBooked = null;
        sendRead();
      }, waitMs);
      return;
    }
    if (socket && gapFree > readSent) {
      readSent = gapFree;
      readAt = Date.now();
      socket.send(JSON.stringify({ type: "read", data: { chat_id: chat, seq: gapFree } }));
    }
  }

  // Ask for everything after my gap-free number (D21), 100 at a time.
  async function catchUp() {
    if (catchingUp) {
      catchUpAgain = true;
      return;
    }
    catchingUp = true;
    try {
      for (let more = true; more; ) {
        const reply = await http.asyncRequest("GET", `${BASE}/api/chats/${chat}/messages?after=${gapFree}&limit=100`, null, {
          ...auth,
          tags: { name: "catch-up" },
        });
        if (reply.status === 503) {
          await wait(retryAfter(reply) * 1000);
          continue;
        }
        if (reply.status !== 200) break;
        const page = reply.json();
        page.messages.forEach((m) => gotMessage(m, "catchup"));
        more = page.has_more;
      }
    } finally {
      catchingUp = false;
    }
    if (catchUpAgain) {
      catchUpAgain = false;
      await catchUp();
    }
  }

  // 4. Sending: one at a time, like the app's outbox. A failed try goes again
  // with the same id, so it's never saved twice (D18): after Retry-After for a
  // 503 "busy" (D34), or after 1 s. It stops 20 s after the chat ends, in time
  // for the partner's last catch-up.
  async function sendOne(stage) {
    const first = Date.now();
    const tags = stage ? { stage } : {};
    // The time goes inside the message, so the partner can work out end to end.
    const payload = JSON.stringify({ client_msg_id: crypto.randomUUID(), body: JSON.stringify({ t: first, s: stage }) });
    while (now() < plan.chatUntil + 20) {
      const reply = await http.asyncRequest("POST", `${BASE}/api/chats/${chat}/messages`, payload, {
        ...auth,
        tags: { name: "send" },
        responseType: "none",
      });
      const ok = reply.status === 201 || reply.status === 200;
      sendFailed.add(!ok, tags);
      if (ok) {
        sendTime.add(Date.now() - first, tags);
        sent.add(1, tags);
        return;
      }
      if (reply.status === 503) {
        sendBusy.add(1, tags);
        busyTime.add(reply.timings.duration, tags);
        await wait(retryAfter(reply) * 1000);
      } else {
        await wait(1000);
      }
    }
    sendGaveUp.add(1, tags);
  }

  // When this user sends next, after `from` (seconds since the start). Each
  // user sends at random moments, on average once per gap(t) (a Poisson
  // process), so all users together send at the planned rate, and a new rate
  // (scenario d) applies at once, even right after a long gap.
  function nextSendAfter(from) {
    let need = -Math.log(1 - Math.random()); // a random wait, counted in sends
    for (let t = from; ; t += 1) {
      const perSecond = 1 / plan.gap(t);
      if (need <= perSecond) return t + need / perSecond;
      need -= perSecond;
    }
  }

  // Each send is planned from the last planned one. A slow send doesn't slow
  // the plan down: the next one goes as soon as it's done.
  function planSend(when) {
    if (when >= plan.chatUntil) return;
    setTimeout(async () => {
      await sendOne(plan.stage ? plan.stage(now()) : undefined);
      planSend(nextSendAfter(when));
    }, Math.max(0, at(when) - Date.now()));
  }

  setTimeout(connect, Math.max(0, at(plan.connectAt ? plan.connectAt(i) : 0) - Date.now()));
  planSend(nextSendAfter(plan.chatFrom));

  // 5. The end: one last catch-up (like the app's 60 s re-check, D21), then hang up.
  setTimeout(async () => {
    await catchUp();
    closing = true;
    if (socket) socket.close();
  }, at(plan.closeAt) - Date.now());
}

// What each run saves in loadtest/results/ (no tokens or tickets in it), and
// a short version on screen.
export function summaryFor(scenario, plan) {
  return (data) => {
    const values = (name) => data.metrics[name]?.values;
    const count = (name) => values(name)?.count ?? 0;
    const round = (stats) => stats && Object.fromEntries(Object.entries(stats).map(([key, value]) => [key, Math.round(value * 10) / 10]));

    const results = {
      run: __ENV.RUN_ID,
      scenario,
      ended_at: new Date().toISOString(),
      duration_s: Math.round(data.state.testRunDurationMs / 1000),
      users: plan.users,
      sent: count("msgs_sent"),
      // In a group, each message should reach every other member (D37).
      expected: count("msgs_sent") * (plan.fanout ?? 1),
      received: count("msgs_received"),
      lost: count("msgs_sent") * (plan.fanout ?? 1) - count("msgs_received"),
      caught_up: count("msgs_caught_up"),
      over_1s: count("msgs_late"),
      send_failed_rate: values("send_failed")?.rate ?? 0,
      send_busy: count("send_busy"),
      send_gave_up: count("send_gave_up"),
      http_failed_rate: values("http_req_failed")?.rate ?? 0,
      connect_failed: count("connect_failed"),
      connect_busy: count("connect_busy"),
      line_drops: count("line_drops"),
      busy_ms: round(values("busy_time")),
      e2e_ms: round(values("e2e_latency")),
      send_ms: round(values("send_time")),
      connect_ms: round(values("connect_time")),
      hello_wait_ms: round(values("hello_wait")),
      reconnect_ms: round(values("reconnect_time")),
      // Scenario d: the same numbers for each step, from its thresholds.
      stages: Object.fromEntries(
        Object.keys(data.metrics)
          .filter((name) => name.includes("{stage:"))
          .map((name) => [name, round(data.metrics[name].values)]),
      ),
    };

    const line = (label, stats) =>
      stats ? `${label.padEnd(14)} p50 ${stats.med} · p95 ${stats["p(95)"]} · p99 ${stats["p(99)"]} · max ${stats.max} ms\n` : "";
    const text =
      `\n${scenario}: ${results.sent} sent · ${results.expected} expected · ${results.received} received · lost ${results.lost}` +
      ` (caught up ${results.caught_up}, over 1 s ${results.over_1s})\n` +
      `failed sends ${(results.send_failed_rate * 100).toFixed(2)}% (busy ${results.send_busy}, gave up ${results.send_gave_up})` +
      ` · failed connects ${results.connect_failed} (busy ${results.connect_busy}) · line drops ${results.line_drops}\n` +
      line("end to end", results.e2e_ms) +
      line("send → 201", results.send_ms) +
      line("send → 503", results.busy_ms) +
      line("connect", results.connect_ms) +
      line("open → hello", results.hello_wait_ms) +
      line("reconnect", results.reconnect_ms);

    return { [`/results/${__ENV.RUN_ID}.json`]: JSON.stringify(results, null, 2) + "\n", stdout: text };
  };
}
