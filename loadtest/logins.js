// Real logins (D33): how many per second Parley can check passwords for.
// A short ramp: 2, 3, 4, 6, 8, then 10 logins a second, 30 s each, with a 15 s
// pause in between. Each login is a new arrival, whether or not the last one
// finished, like people logging in on their own. argon2 uses 64 MB and about
// 0.3 s per check, so this finds where logins pile up. A quick 503 "busy" (D34)
// is counted on its own: it isn't a failure, it's the cap doing its job.
import http from "k6/http";
import exec from "k6/execution";
import { Counter, Trend } from "k6/metrics";

// The same for every fake user (seed.py).
const PASSWORD = "load-test-password";
const RATES = [2, 3, 4, 6, 8, 10];

const loginTime = new Trend("login_time", true); // logins that worked
const loginOk = new Counter("logins_ok");
const loginBusy = new Counter("logins_busy"); // 503 "busy, try again" (D34)
const busyTime = new Trend("login_busy_time", true); // how fast that 503 came
const loginFailed = new Counter("logins_failed"); // wrong answer or no answer within 60 s

const step = (rate, index) => ({
  executor: "constant-arrival-rate",
  rate,
  timeUnit: "1s",
  duration: "30s",
  startTime: `${index * 45}s`,
  // Enough waiting users that new logins keep arriving even when old ones hang.
  preAllocatedVUs: 20,
  maxVUs: 400,
});

export const options = {
  scenarios: Object.fromEntries(RATES.map((rate, index) => [`r${rate}`, step(rate, index)])),
  // A threshold per step makes the summary keep each step's own numbers.
  thresholds: Object.fromEntries(
    RATES.flatMap((rate) => [
      [`login_time{scenario:r${rate}}`, ["max>=0"]],
      [`logins_busy{scenario:r${rate}}`, ["count>=0"]],
      [`login_busy_time{scenario:r${rate}}`, ["max>=0"]],
      [`logins_failed{scenario:r${rate}}`, ["count>=0"]],
    ]),
  ),
  systemTags: ["scenario", "name", "method", "status", "expected_response", "error_code"],
  summaryTrendStats: ["min", "med", "p(95)", "p(99)", "max", "count"],
};

export default function () {
  // load0001, load0002 ... in turn: every login is a fresh session.
  const n = (exec.scenario.iterationInTest % 1000) + 1;
  const email = `load${String(n).padStart(4, "0")}@example.com`;
  const reply = http.post(`${__ENV.BASE_URL}/api/auth/login`, JSON.stringify({ email, password: PASSWORD }), {
    headers: { "Content-Type": "application/json" },
    tags: { name: "login" },
  });
  if (reply.status === 200) {
    loginTime.add(reply.timings.duration);
    loginOk.add(1);
  } else if (reply.status === 503) {
    busyTime.add(reply.timings.duration);
    loginBusy.add(1);
  } else {
    loginFailed.add(1);
  }
}

export function handleSummary(data) {
  const round = (value) => Math.round(value ?? 0);
  // Each step's logins, from the counters' and the timing's own tags.
  const steps = RATES.map((rate) => {
    const timing = data.metrics[`login_time{scenario:r${rate}}`].values;
    const failed = data.metrics[`logins_failed{scenario:r${rate}}`].values.count;
    const busy = data.metrics[`logins_busy{scenario:r${rate}}`].values.count;
    const busyMs = data.metrics[`login_busy_time{scenario:r${rate}}`].values;
    return {
      rate,
      ok: timing.count,
      busy,
      failed,
      p50_ms: round(timing.med),
      p95_ms: round(timing["p(95)"]),
      max_ms: round(timing.max),
      busy_p95_ms: round(busyMs["p(95)"]),
    };
  });
  const results = {
    run: __ENV.RUN_ID,
    scenario: "logins",
    ended_at: new Date().toISOString(),
    duration_s: Math.round(data.state.testRunDurationMs / 1000),
    steps,
    failed_total: data.metrics.logins_failed?.values.count ?? 0,
    // Arrivals k6 couldn't even start, because every waiting user was stuck.
    dropped: data.metrics.dropped_iterations?.values.count ?? 0,
  };
  const text = steps
    .map((s) => `${s.rate} logins/s: ${s.ok} ok · ${s.busy} busy (p95 ${s.busy_p95_ms} ms) · ${s.failed} failed · p50 ${s.p50_ms} · p95 ${s.p95_ms} · max ${s.max_ms} ms`)
    .join("\n");
  return {
    [`/results/${__ENV.RUN_ID}.json`]: JSON.stringify(results, null, 2) + "\n",
    stdout: `\n${text}\nfailed ${results.failed_total} · dropped ${results.dropped}\n`,
  };
}
