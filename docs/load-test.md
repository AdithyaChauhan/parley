# Parley load test (T31, and the fix after it)

1,000 fake users on one laptop, measured end to end and read from the Grafana dashboard (T30).
Runs: T31 on November 1-4, 2026 (the old code), and the re-runs after the fix (D34) on November 6. Times are the laptop's (IST, UTC+5:30), like the screenshots.

## The short version

- **After the fix, no run freezes a copy, and every saved message reaches its partner.** Overload now means a quick 503 "busy, try again" (p95 about 4 s), and each copy recovers by itself.
- **With 1,000 users connected, Parley handles about 30 messages per second cleanly** (end to end p50 50 ms, p95 407 ms) and accepts up to ~37 a second. In T31 the same step had p95 969 ms, and 40 a second froze both copies.
- **The limit is now CPU.** Python runs one thread at a time, so each copy tops out at about one core, while PostgreSQL stays under 0.4 cores.
- **What froze a copy was a deadlock, not a leak.** T31 blamed requests that were given up and never handed their connection back. Tests on the old code disproved that: a request held a connection while it waited for a thread, and the threads waited for a connection (see "The bottleneck").
- **Real logins no longer collapse.** At 10 a second, all 301 went through and each backend stayed at or under ~206 MB. On the old code in the same session: 10 finished, p95 53 s, 945 MB. At 30 a second the extra logins get a 503 within ~2.5 s.
- The first request after a quiet minute is not slow (the T30 question), whether the monitoring stack is on or off.

## Before and after the fix (D34)

T31's numbers are the "before" for b, c, d and e. `logins.js` got its 8 and 10 steps, so it was run on both the old and the new code on November 6.

The "after" runs used the same laptop, scripts and Docker memory, with a fresh Docker start. **One thing made them harder than T31:** VS Code, WhatsApp and a browser stayed open, so Windows had only ~0.6 GB free (0.35-1.2 GB) and paged in bursts of up to ~8,600 pages/s. T31 had other apps closed.

| Target | Result |
|---|---|
| 0 undelivered messages in b and e | **Met.** b: 14,624 saved, 14,624 received. e: 3,533 saved, 3,533 received. |
| No frozen copy in any run | **Met.** After every run: 0 sessions idle in transaction, and every running copy answers. |
| Quick 503s under overload | **Met.** d: p50 3.5 s, p95 3.9 s, max 4.6 s. b: p50 3.6 s, p95 4.1 s, p99 5.6 s, max 28 s. |
| The limit in d measured again | **~35 messages/s** (30 is clean, 40 is over). It was ~30, with a freeze at 40. |
| Logins at 10/s keep memory flat, with quick 503s | **Met.** ~206 MB per backend at most. It needed no 503s at 10/s, so a flood at 20 and 30/s shows them. |

### b. Steady chat, ~50 messages/s (above the limit)

| | T31 (old code) | After the fix |
|---|---|---|
| Copies | Both frozen within a minute | Both fine for all 10 minutes |
| Saved / received | 411 / 405: **6 undelivered** | 14,624 / 14,624: **0 undelivered** |
| What the overload looks like | 99.7% of send tries failed | 20-25 messages/s accepted, the rest get a 503 |
| Live lines | | 500 and 500 for the whole 10 minutes |

890 lines dropped, all in the last seconds: every fake user runs its final catch-up at the same moment, a burst the real app never makes. 15,410 sends were still not accepted when the chat ended. In the real app, those stay "waiting" in the outbox and go out later.

### c. Connection storm: 1,000 users connect within 10 s

| | T31 (old code) | After the fix |
|---|---|---|
| Lines up | 24 to 121 of 1,000, then frozen | **1,000 of 1,000** |
| Failed connects | 1,871 to 2,182 | **0** (233 ticket 503s, tried again) |
| Connect p50 / p95 | | 5.5 s / 7.4 s |
| Line open → hello p50 / p95 | 1.2 s / 2.2 s (of the few that got one) | 2.6 s / 4.1 s |

D23's subscribe lock is still a real queue in a storm, but it no longer ends in a freeze.

### d. Find the limit

1,000 users connected, with the target rate raised every 100 s. End to end is p50 / p95 / p99:

| target | T31 reached | T31 end to end | T31 tries refused | after: reached | after: end to end | after: tries refused | 503 p95 |
|---|---|---|---|---|---|---|---|
| 10/s | 9.9/s | 25 / 53 / 77 ms | 0% | 10.2/s | 26 / 146 / 360 ms | 0% | |
| 20/s | 18.7/s | 28 / 80 / 164 ms | 0% | 19.9/s | 53 / 2,190 / 3,037 ms (see below) | 0% | |
| 30/s | 28.7/s | 45 / 969 / 1,454 ms | 0% | **30.3/s** | **50 / 407 / 624 ms** | 0% | |
| 40/s | 6.5/s (frozen) | 1 s / 30 s / 271 s | 90% | **37.4/s** | 3.5 s / 35 s / 80 s | ~50% | 3.7 s |
| 50/s | 0 (frozen) | | 100% | 29.3/s | 20 s / 96 s / 142 s | ~80% | 3.8 s |
| 60/s | not run | | | 21.3/s | 16 s / 70 s / 97 s | ~90% | 4.0 s |

- Saved 14,840, received 14,840. 0 line drops, 0 failed connects, and every message came live (0 by catch-up).
- **The 20/s blip was the laptop.** Windows paged at ~5,900 pages/s for about 30 s. Requests in progress rose to ~14 per copy, then drained by themselves within 30 s, with one 503. On the old code, a pause like that is what could set off the freeze.
- Past the limit, end to end is mostly time spent waiting to try again, in the sender's outbox. It's long, but nothing is lost.
- Accepted messages/s falls past the limit, because refused requests aren't free: 160-180 a second were also being parsed and answered.

### e. Failover under load: ~10 messages/s, `backend_a` stopped mid-chat

| | T31 (old code) | After the fix |
|---|---|---|
| `backend_b` | Frozen within a minute | Took over: 503s stopped within a minute of the stop |
| Saved / received | 1,342 / 1,339: **3 undelivered** | 3,533 / 3,533: **0 undelivered** |
| The 500 moved lines | None got back | All 500 back, 0 failed connects |
| Reconnect p50 / p95 / max | | 20 s / 51 s / 52 s |
| Messages/s after the stop | 0 | ~10, the same as before |

The moved lines all arrive together, so 887 ticket 503s and 185 send 503s (p95 4.9 s) were part of the takeover. Tickets that were refused push some lines onto D21's longer waits, which is why the slowest reconnect took 52 s.

### Logins per second

| logins/s | Old code | New code |
|---|---|---|
| 2 | 60 ok, p95 2,874 ms | 60 ok, p95 1,692 ms |
| 3 | 91 ok, p95 195 ms | 91 ok, p95 170 ms |
| 4 | 121 ok, p95 217 ms | 121 ok, p95 149 ms |
| 6 | 164 ok, p95 4,855 ms | 181 ok, p95 147 ms |
| 8 | 140 ok, p95 736 ms | 240 ok, p95 168 ms |
| 10 | **10 ok, 4 failed, p95 53.8 s** (288 logins in all never started, because k6's users were stuck) | **301 ok, p95 1,144 ms** |
| Biggest backend at 10/s | **945 MB** | **206 MB** |
| Docker swap at 10/s | 174 MB | 2 MB |

A flood on the new code (a one-off, not in `logins.js`):

| logins/s | ok | 503 "busy" | failed | 503 p95 |
|---|---|---|---|---|
| 10 | 301 | 0 | 0 | |
| 20 | 372 | 201 | 0 | 2.1 s |
| 30 | 301 | 537 | 0 | 2.5 s |

Each backend stayed at or under 287 MB (about 85 MB, plus 3 x 64 MB), and swap under 28 MB. So a copy takes about 10-15 real logins a second on this laptop, and the rest are told "busy" within ~2.5 s. k6 itself couldn't start 90 of the arrivals while it was adding more fake users.

**The sections a to e below are T31's runs on the old code, kept as the "before".** Their numbers stand. T31's explanation of the freeze was wrong, and "The bottleneck" has the corrected one.

## The laptop

| | |
|---|---|
| Laptop | Acer Aspire 7 (A715-41G), Windows 11 Home (build 26300) |
| CPU | AMD Ryzen 5 3550H, 4 cores / 8 threads, 2.1 GHz base |
| RAM | 8 GB installed, 5.9 GB usable |
| Disk | 512 GB NVMe SSD |
| Docker | Docker Desktop 29.7.2 on WSL2: 8 CPUs, **3.4 GB RAM** (`memory=3584MB` in `.wslconfig`), 1 GB swap |

**Everything shares this one laptop:** Parley (Nginx, 2 backend copies, worker, PostgreSQL, Redis, RabbitMQ), the monitoring stack (Prometheus, Grafana, exporters, cAdvisor: ~0.6-0.8 GB) and k6 (up to ~0.6 GB and ~2 cores at its busiest). These are laptop numbers, not server numbers.

## How it was tested

- **k6 2.3.0** (`grafana/k6:2.3.0`) runs in Docker on Parley's own network and goes through Nginx, like a browser. It sends its numbers to Prometheus, so the dashboard shows them next to Parley's (the "Load test" row).
- **Its own data:** a fresh `parley_load` database for every run (1,000 users, 500 one-to-one chats), Redis database 1, and the rate limits off (`RATE_LIMITS_ENABLED=false`, which the app refuses when `COOKIE_SECURE=true`). The dev data was never touched: 11 users, 5 chats, 289 messages, 75 sessions, before and after.
- **Each fake user** (`loadtest/lib.js`) behaves like the app:
  1. It opens with a saved session: one refresh, no password.
  2. It gets a ticket and opens the live line, then pings every 25 s.
  3. It sends to its partner at random moments, at the planned average rate.
  4. It sends `read` for every message it gets.
  5. When a message number is skipped, or the line reconnects, it catches up by number.
  6. When it gets a 503 "busy" (D34), it waits for `Retry-After` and tries again with the same id, like the app. (In T31 it tried 5 times, 1 s apart.)
- **Timing:**
  - *Send → 201* is timed by the sender.
  - *End to end* is timed by the partner: the send time is written inside the message, and both users run in the same k6 program, so they share one clock.
- **Lost** means a message saved in the database that the partner never received. The database count is the truth (`*.db.txt` files).
- Users start 10 a second, so 1,000 are ready in ~100 s. At 50 a second, the start itself froze both copies (see c, run 1). Every run ends within ~13 minutes, because the access token lasts 15 minutes.
- One command per scenario: `bash loadtest/run.sh trial|logins|a|b|c|d|e` (Git Bash, from the repo root). It seeds `parley_load`, switches the backends to it, runs k6, checks the database, saves `loadtest/results/<run>.json` and `.db.txt`, then puts the normal backends back.

## a. Baseline: the first request after a quiet minute

One user, 5 rounds. Each round: a quiet minute, then 4 health checks and 3 real logins in a row. The first of each counts as "first", the rest as "warm". In milliseconds, p50 / max:

| | health first | health warm | login first | login warm |
|---|---|---|---|---|
| monitoring on | 6.4 / 11.9 | 3.2 / 4.1 | 146 / 296 | 129 / 260 |
| monitoring off | 5.2 / 5.8 | 3.6 / 4.5 | 123 / 198 | 120 / 146 |

There's no real first-request penalty. With the monitoring stack on, a login after a quiet minute is ~20 ms slower. The ~0.9 s login seen in T30 didn't come back. That points at the laptop itself waking up from idle, not at the monitoring stack. During these runs the laptop was never fully idle (Docker and k6 were running), so that part isn't proven.

## Logins per second (argon2)

Real logins, one new arrival at a time whether or not the last one finished:

| logins/s | Nov 4, fresh Docker (~1.9 GB free) | Nov 1, Docker partly used (~1 GB free, ~0.3 GB in swap) |
|---|---|---|
| 2 | 49 ok, p95 227 ms (11 failed: see below) | 61 ok, p95 424 ms |
| 3 | 90 ok, p95 138 ms | 91 ok, p95 292 ms |
| 4 | 121 ok, p95 236 ms | 121 ok, p95 300 ms |
| 6 | 181 ok, p95 137 ms | **13 of ~90 done, p95 26 s**, backends ~900 MB each |
| 8 | 160 ok, p95 374 ms (probe) | |
| 10 | **36 of 200 done, p95 8.2 s**, backends ~800 MB each, ~450 MB swap (probe) | **0 done** |
| 12 | **0 done** (probe) | |

- Each argon2 check takes 64 MB and ~0.1-0.3 s. When checks pile up, memory runs into swap, each check gets slower, and more pile up. The rate where that starts depends on how much memory is free: 6/s on Nov 1, 10/s on Nov 4.
- The backends also keep working on requests nobody waits for any more.
- On the 2 GB server, a login flood could have taken the site down even with D24's per-IP limits. The cap is in D34 (see the top).
- The 2-6 rows come from `loadtest/logins.js`. The 8-12 rows are a one-off probe with the same code. `logins.js` now has the 8 and 10 steps too.
- The 11 failures at 2/s were 502s in the first 5 seconds: Nginx still had the old backend addresses (D28). `run.sh` now waits 12 s after switching the backends.

## c. Connection storm: 1,000 users connect within 10 s

Three runs (`loadtest/results/2026-11-04_*-c.*`):

| run | what happened |
|---|---|
| 18:20, users start 50/s | The start itself (refresh, then the chat list) ran each copy out of database connections. 600 of ~1,000 refreshes were given up after 60 s, and 0 lines connected. Both copies frozen. |
| 18:36, users start 10/s | The start was fine (1,000 of 1,000). In the storm, only 306 tickets were answered and 121 lines got hello (open → hello p50 1.2 s, p95 2.2 s), with 1,871 failed connects. Both copies frozen. |
| 18:43, + subscribe-lock timer | 24 hellos and 2,182 failed connects. Waits for the D23 subscribe lock: mean 0.21-0.45 s, p95 1.5-2.2 s, p99 2.3-2.4 s. Both copies frozen. |

- **D23's subscribe lock is a real queue in a storm.** Each copy subscribes one line at a time and waits for Redis to confirm, so lines wait up to ~2 s just for the lock. When users connect gradually (b, d, e), open → hello is only p50 6 ms and p95 13 ms.
- **The freeze, though, is the database pool** (below), not the lock.
- Spread between A and B: with gradual connects the split was exactly 500 | 500 (least_conn works). In the storm, too few lines connected to judge.

![Storm: requests collapse and both copies freeze](load-test/c-storm.png)

## b. Steady chat: 1,000 users, ~50 messages/s

Both copies froze within the first minute of chatting:

- 368 sends got their 201, and 99.7% of send tries failed after that.
- The database has 411 messages: 43 were saved, but their sender never heard back.
- Partners received 405.

The 100 s connect phase before it was healthy: connect p50 17 ms, open → hello p50 6 ms, and 500 | 500 lines per copy.

![Steady chat at 50/s: the freeze right after chatting starts](load-test/b-steady.png)

## d. Find the limit

1,000 users connected, with the target rate raised every 100 s:

| target | reached | end to end p50 / p95 / p99 | failed send tries |
|---|---|---|---|
| 10/s | 9.9/s | 25 / 53 / 77 ms | 0% |
| 20/s | 18.7/s | 28 / 80 / 164 ms | 0% |
| **30/s** | **28.7/s** | 45 / **969** / 1,454 ms | 0% |
| 40/s | 6.5/s | 1,004 ms / 29.8 s / 271 s | 90% (frozen) |
| 50/s | 0 | | 100% (frozen) |

**The limit (p95 end to end over 500 ms) is about 30 messages per second, and 20 a second is comfortable.**

What ran out first: **database connections**.
- CPU stayed low the whole time: backends ≤ 0.9 cores each, PostgreSQL ≤ 0.4, k6 ≤ 2, out of 8.
- Postgres connections went from ~13 to ~33: both pools full (30), plus the worker and the exporter. 25-30 of them were "idle in transaction".
- Thread dumps every 40 s showed each copy going from mostly idle threads, to a few database calls, to 30-40 threads waiting for a pool connection. Then it stayed there.

![Find the limit: messages climb to ~30/s, then both copies freeze](load-test/d-limit.png)

## e. Failover under load

1,000 users at ~10 messages/s, with `backend_a` stopped at 19:23:30, about 2 minutes into the chat. (At b's 50/s, both copies freeze with no failover at all.)

- Before the stop, it was healthy: end to end p50 31 ms, p95 94 ms.
- `backend_a` closed its 502 lines (code 1012), and they all tried to reconnect to `backend_b` within a second or two. **`backend_b` froze within a minute** (15 connections idle in transaction). None of the moved lines got back. `backend_b` kept its own ~500 lines open, but nothing that needs the database worked any more: sends, tickets, catch-up.
- Totals: 1,342 sent, all of them in the database, and 1,339 received. **3 messages were saved but never reached the partner**, because the catch-up that would have brought them couldn't run on the frozen copy. The database didn't lose them (D9), but during the test they never arrived.

The T26 failover demo works with a few users. With ~500 lines moving at once, the surviving copy freezes.

![Failover: A's lines drop, B freezes, messages stop](load-test/e-failover.png)

## The bottleneck: what froze a copy, and what limits it now

### The freeze was a deadlock, not a leak

The old setup per copy: 40 threads for normal (`def`) routes, 15 database connections, and up to 30 s of waiting for a connection.

1. A request's login check (`get_current_user`) ran in one thread and took a connection. Its session stayed open.
2. The thread was handed back, and the route had to wait for a thread of its own, **still holding that connection** ("idle in transaction").
3. With about 55 requests in at once, 15 of them held every connection and waited for a thread, while all 40 threads were held by requests waiting for a connection. Nobody could move until the 30 s timeout failed those 40.
4. So a copy drained about 1.3 requests a second. And uvicorn doesn't cancel a route when its client hangs up, so abandoned requests stayed in the line. A line of thousands takes hours, which looks frozen for good.

T31 said something else: that a given-up request never closes its session, so it leaks its connection. The tests below disprove it. T31's evidence (15 sessions idle in transaction per copy, 40 threads waiting for the pool) fits the deadlock too.

| Experiment on the old code | Result |
|---|---|
| 5 sends stuck on a row lock, then their clients hang up | The pool is back to 0 once the lock goes. **No leak.** |
| A request's task really cancelled mid-flight | The pool is back to 0. **No leak.** |
| 150 requests land at once, and **nobody hangs up** | **The freeze:** 15 idle in transaction, all 40 threads waiting for a connection, `/api/health` silent. In 70 s, 80 answers, all 500. |

### What set it off at ~30 messages/s

Not RabbitMQ or Redis. Thread dumps from a probe of the old code at 20-40 messages/s (135 dumps): 1,791 thread samples waiting for a connection, 77 in a database call, 1 in RabbitMQ, 0 in Redis. Threads were mostly idle, and then all flipped to waiting at once.

T31's own numbers show the climb. At 30 messages/s the busier copy used 0.8 of the ~1 core Python can use, and requests in progress rose from 1 to 3.5 to 5.6 per copy. Within 30 s of the step up to 40, sessions idle in transaction jumped to 25-30 and traffic fell to 0.

So: **as a copy nears its one core, requests start to queue, and any short pause can push it over ~55 at once. Past that point it can't recover.** On November 6, with the laptop short of memory, the same flip came at only 20 messages/s.

### What changed

- A database session opens inside the work (`with SessionLocal() as db:`, in one thread) and closes before anything waits. `get_db` is gone, and `get_current_user` has its own short session. So no connection is ever held across a wait for a thread, whether a request ends normally or is cancelled.
- A send reads what it needs, closes the session, and only then publishes to Redis and RabbitMQ. The same goes for receipts and the chat list's Redis read. D9's "save first" still holds.
- Threads, connections and requests at work are one number per copy (below).
- A request waits for a slot at most 3 s, then gets 503 with `Retry-After`. Waiting costs no thread and no connection. Signing up and logging in have a smaller gate of their own.
- PostgreSQL ends any app session idle in a transaction for 60 s. It's set per connection, in `db.py`, so a deploy doesn't have to restart the database.
- On the live line, a busy database drops that one event, not the line.
- The app retries a send on a 503, like a 429, with the same id and in order. Log-in and sign-up show "Busy, try again in a moment."

### The numbers, and why

| Setting | Value | Why |
|---|---|---|
| Threads, connections, requests at work (per copy) | **8** | The same number, so none of them waits for another. Compared below. |
| PostgreSQL connections in use | ~17 of 100 | 2 x 8, plus the worker and exporters. Room left for migrate and admin. T31 used ~33. |
| Wait for a request slot | 3 s | Well under Nginx's 60 s, and a person is still looking at the screen. |
| `Retry-After` | 1-3 s, at random | So everyone refused at the same moment doesn't come back at the same moment. |
| Pool timeout | 2 s | A backstop only. A thread always finds a connection, so it shouldn't happen. It also answers 503. |
| Idle in transaction timeout | 60 s | The safety net, so nothing stuck can hold a lock forever. |
| Password checks at once (per copy) | 3, waiting up to 2 s | 64 MB each. 2 copies x 3 x 64 MB = 384 MB at worst, of the server's ~1 GB free. |

Why 8: the same overload (30, then 50, then 20 messages/s) with three thread counts, one run each. The 15 was the first choice:

| threads | sent in the 50/s step | 503 p50 / p95 / max | line drops | connections |
|---|---|---|---|---|
| 5 | 4,281 | 3.2 / 3.5 / 10.7 s | 104 | 11 |
| **8** | 4,055 | **3.4 / 3.8 / 4.4 s** | **0** | 17 |
| 15 | 4,160 | 3.9 / 4.3 / 6.6 s | 82 | 31 |

More threads don't go faster, because Python runs one at a time. The throughput is the same within noise, about 27 messages/s here. Busy threads do take turns away from the event loop, which answers pings and delivers pushes. With 15 threads, the full d run reached only ~16 messages/s past the limit, with 896 line drops and a 503 tail up to 32 s (`*-15-threads.*` in the results).

### What limits it now

CPU: 1.1-1.2 cores per copy at the limit, with PostgreSQL at ≤0.4, ~17 connections and nothing waiting on the pool. So the bottleneck has moved from a bug to a real limit.

## What to change next

1. **A restart for a truly stuck copy** (T32's liveness probe) is still worth having, as a safety net. `/api/health` stays a `def` route on purpose: it needs a free thread, so a copy whose threads are really stuck fails it.
2. **More capacity now means more CPU.** A third copy should finally help, because the limit is per copy and PostgreSQL has room. A faster HTTP layer (`uvicorn[standard]`: uvloop and httptools) might help too. Neither is measured.
3. **The subscribe lock (D23):** subscribe in batches, or lock per channel. Open → hello is still p50 2.6 s in a storm.
4. **Spread reconnects out:** D21's random extra is 0-1 s, so ~500 lines come back together after a failover. A wider first wait would soften that.
5. **A longer wait after repeated 503s:** the app uses `Retry-After` each time. Backing off further would spend less CPU on refusals in a long overload.
6. **D15's async question:** not needed. Nothing froze in the re-runs, and the limit is Python's one core per copy, which async SQLAlchemy wouldn't lift.
7. **A small known gap:** a page reload during overload whose refresh gets a 503 shows the log-in screen, as for any 5xx today. A second reload fixes it.

## Honest limits

- k6, Parley and the monitoring stack share one laptop with 3.4 GB for Docker. k6 itself used up to ~2 cores.
- Docker's memory state changes the login numbers (6/s on Nov 1, 10/s on Nov 4).
- A thread dump every 40 s is a sample, not a full picture.
- The 15-minute access token caps each run at ~13 minutes.
- "Lost" in the k6 summaries is sent minus received. It goes negative when timed-out sends were still saved, so the database count (`*.db.txt`) is the one to read.
- The November 6 runs had less free memory than T31 (see the top), and each thread count ran only once, so small differences between them are noise.
- A first try at the old-code logins, right after a Docker restart with Windows paging ~4,000 pages/s, collapsed even at 2/s. It was thrown away and run again once things had settled. It shows how much the laptop's state matters.
- These are laptop numbers. The server has 2 vCPUs and 2 GB, and it never gets a load test (D33).

## Files

- Scripts: `loadtest/` (`run.sh`, `lib.js`, `seed.py`, `compose.loadtest.yml`, `trial.js`, `logins.js`, `a-baseline.js` … `e-failover.js`). `loadtest/sessions.json` (raw refresh tokens) is made by the seed and gitignored.
- Results: `loadtest/results/` (one `.json` per run, plus a `.db.txt` with the database check, sessions left idle in transaction, and whether each copy still answered). The November 6 runs are `2026-11-06_*`: `-logins-before` is the old code, `-15-threads` and `tune-t*` are the thread-count comparison, and the rest are the final runs.
- Screenshots: `docs/load-test/`, taken with a temporary read-only Grafana and headless Chrome.
