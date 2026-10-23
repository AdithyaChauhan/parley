# Parley: Project Plan

Parley is a real-time chat web app, like WhatsApp Web. It's a portfolio project to learn and show backend system design.

**How to use this file**
- One task at a time. Each task = one branch = one pull request.
- "You are here" shows the current task and its brief.
- After a pull request merges, Adithya tells the planning chat. The planner sends back a new PLAN.md (box ticked, "You are here" moved to the next task). Adithya replaces the file, and that goes in the next task's branch.
- Only the planner (chat Claude) writes task briefs. Claude Code never edits this file. It can only suggest changes.
- Adithya may write a file himself if he wants. He tells Claude Code, so it knows.
- Before merging: copy the CI run link from https://github.com/AdithyaChauhan/parley/actions into the report.
- `/docs` checks with two people: for each person, log in, paste the token into Authorize, confirm with `GET /api/auth/me`, then do their steps.
- npm audit's "braces" warnings: dev-only and no fixed version yet. Don't raise them again until a fix exists.
- Never commit straight to `main`. Even a small fix goes through a branch and a PR (D13).
- Before merging, paste the PR description. Proof steps (like a red-cross test) use a throwaway PR that's closed without merging, and the run links go in the report.
- Each task's "Done when" also needs the task's "In my words" in LEARNING.md filled in by Adithya. For frontend tasks (fast mode, see CLAUDE.md), Claude Code drafts it and Adithya just reviews it.

---

## You are here

### Task 22b: Fix: reads and ticks reach the server without the live line (teaching mode for the backend, fast mode for the app)
- **Branch:** `fix/receipts-over-http`
- **The bug (found by Adithya in T22's Redis-down check):**
  - Redis stops, so the live line is down.
  - Ben opens Ana's chat. The app wants to send "read #42", but the live line is its only way to send that, so it never reaches the server.
  - The server still says Ben read up to #41, so unread = 42 − 41 = 1.
  - Ben goes back to the chat list, and the badge "1" comes back.
  - It also breaks T23: the worker checks `read_up_to` and would notify Ben about a message he already read.
- **Why:** `read_up_to` lives in PostgreSQL (the truth), but the only way to move it goes through Redis (ticket and live line). Redis is only a helper (D24), so the bookmark must not depend on it.

**Example first (Claude Code shows this before any code):**
```
 live line open?  yes → send {"type":"read","data":{"chat_id":..,"seq":42}} on the line (as today)
                  no  → POST /api/chats/<chat_id>/read {"seq": 42} → saved in PostgreSQL → 200
                        both doors call the same function: forward only, never past last_seq
 badge = newest − max(server's read_up_to, highest number this app has already shown)
       → never jumps back while a read is on its way
```

**Steps:**
1. **Backend:**
   - Add `POST /api/chats/{chat_id}/read` and `POST /api/chats/{chat_id}/delivered`, each taking `{"seq": N}` (the same name the live line already uses).
   - Both call the same function the live line uses today, with the same rules: only members (404 otherwise), forward only, never past `last_seq`, `read` also lifts `delivered`, and the receipt is pushed via the bus (never raises). Each returns both bookmarks.
   - If the bookmark didn't move, push no receipt (check whether that's already true on the live line, and make both doors match).
   - No new rate limit: it's one small update that only moves forward.
2. **App (fast mode):**
   - `read` and `delivered` go over the live line when it's open, and over HTTP once the line is known to be down (it dropped, or a connect failed). They don't use HTTP while the line is first connecting.
   - If HTTP fails too (offline), the app keeps the highest number per chat and sends it once it's back online or reconnected.
   - The unread badge uses the higher of the server's `read_up_to` and what this app has already shown.
   - Messages that arrive through the chat-list catch-up (T22) also send `delivered`.
3. **Tests:**
   - HTTP read and delivered: they move forward only, are capped at `last_seq`, and a non-member gets 404. Read lifts delivered.
   - With Redis down, they still give 200 and the bookmark is saved.
   - After an HTTP read, the chat list shows unread 0.
   - A read that doesn't move the bookmark pushes nothing.
- **Added during the task (approved):** while the line is down, the open chat re-checks `messages?after=<gap-free seq>` every 60 s (in `useMessages.ts`), so Ana's ticks update within about a minute during an outage (D24).
- **Done when:**
  - `docker compose stop redis`: Ana sends, and Ben sees it within about a minute. Ben opens the chat and goes back, and there's no badge. Reload, and still no badge.
  - Still during the outage: once Ben reads it, Ana's tick turns teal within about a minute.
  - `docker compose start redis`: once both reconnect, Ana's message shows read (teal) without Ben doing anything.
  - With Redis up, ticks and typing work as before.
  - All tests pass, CI is green (run link in the report), and "In my words" is filled in by Adithya.

"In my words" prompt: why the read bookmark gets an HTTP door but typing doesn't.

---

## Next up (don't start until Task 22b is merged)

### Task 23: Notification worker with retries and a failed-jobs queue (RabbitMQ) (teaching mode, friend style)
- **Branch:** `feature/notify-worker`
- **Goal:** when Ana messages Ben and Ben doesn't read it within a few seconds, a separate worker program "notifies" Ben. If the notifier fails, the job is retried later. If it keeps failing, it's parked in a failed-jobs queue instead of being lost or retried forever. In this task the notifier only writes a log line. T24 swaps in real browser push.
- **Mode:** teaching mode, friend style, questions at the end as "In my words" prompts. Claude Code runs the checks itself and shows the results.

**Example first (Claude Code shows this before any code):**
```
 10:00:00  Ana sends #42 to Ben → saved in PostgreSQL (201)
           backend drops a job in RabbitMQ: {message_id, chat_id, seq: 42, recipient: Ben}   (no text, D12)
           → the job waits in notify.wait (5 s)
 10:00:05  worker picks it up:
             Ben's read_up_to is 42 already? → skip ("he saw it live")
             already notified for this message? → skip (no doubles)
             otherwise → notifier: "New message from Ana"
 notifier fails?   try 1 → wait 10 s → try 2 → wait 1 min → try 3 → wait 5 min → try 4 → notify.failed
 worker crashes mid-job? the job was never acked (ticked off), so RabbitMQ hands it out again

 Queues:
   notify         ← the worker reads only this one
   notify.wait    (5 s timer)   ─┐
   notify.retry.10s / .1m / .5m ─┴─ when the timer ends, the job falls back into notify
   notify.failed  ← parked jobs, visible in RabbitMQ's web page (localhost:15672)
```

**Steps:**
1. **RabbitMQ in Docker Compose:** the official `rabbitmq` image with the management web page, pinned to the latest stable version (check Docker Hub, don't guess). Add a health check. Python uses `pika` (pinned, latest stable from PyPI). `.env` gets `RABBITMQ_URL`, and `.env.example` gets a placeholder.
2. **`app/notify/queues.py`:** declares all queues, durable, in one place. The wait and retry queues each have their own timer (`x-message-ttl` on the queue) and a dead-letter route back to `notify`. A timer per queue, not per job, so a 5-minute job never blocks a 10-second one behind it. Both the backend and the worker call this at startup, and declaring twice is harmless.
3. **`app/notify/publisher.py`:** after a message is saved (after commit), one job per other member of the chat goes to `notify.wait`.
   - Jobs are persistent, and RabbitMQ confirms it got them (publisher confirms).
   - Never raises and gives up fast (about a 1 s timeout, the T22 lesson). If RabbitMQ is down, the send still gives 201 and a warning is logged. That notification is lost, which is accepted (see D25).
   - pika isn't thread-safe, and sync routes run on several threads, so use one connection with a lock (or one per thread). Claude Code picks and explains in 3 lines.
4. **`app/notify/worker.py`, run as `python -m app.notify.worker`** (its own terminal now, its own container in T25):
   - Reads `notify` with prefetch 10, and acks only after the job is finished.
   - **Skip if already read:** the recipient's `read_up_to >= seq` in PostgreSQL.
   - **Skip if already sent:** Redis `notified:<message_id>:<user_id>`, checked before sending and set after a successful send, with a 24 h timer.
   - Otherwise it calls the notifier.
   - **On failure:** it re-publishes to the next retry queue with `attempt + 1` in the job's headers, then acks the original. After try 4 the job goes to `notify.failed` with the last error.
   - A broken job (bad JSON, missing fields) goes straight to `notify.failed`. There's no point retrying it.
   - Redis or PostgreSQL down counts as a failure, so it gets retried later.
   - If RabbitMQ drops, it reconnects with backoff (1, 2, 4 ... 30 s).
   - Stops cleanly on Ctrl+C: it finishes or returns the current job.
5. **`app/notify/notifier.py`:** `LogNotifier.send(user_id, title)` logs "notify <user>: New message from <name>". There's never any message text (D12).
   - For demos and tests, `NOTIFY_FAKE_FAIL_TIMES=N` makes every job fail its first N tries. Set it to 2 to watch retries work, or 10 to watch a job land in `notify.failed`.
6. **`python -m app.notify.replay`:** moves every job from `notify.failed` back to `notify` with attempt reset to 1, and prints how many it moved. That's for "the push service was down for an hour, it's fixed now, send them all".
7. **Timers come from settings,** so tests can use a few hundred milliseconds instead of minutes.
8. **Tests:**
   - Tests use `TEST_RABBITMQ_URL` on a `parley_test` vhost, and refuse any other vhost (like the `_test` and db 15 guards). Queues are purged between tests.
   - Sending a message puts one job per other member in `notify.wait`, with no message text in it.
   - With RabbitMQ down, a send still gives 201 and the row is saved.
   - Worker logic: it skips when the message is already read, skips when already notified, and sends otherwise.
   - With fake fails at 2, the job is sent on try 3. With fake fails at 10, it lands in `notify.failed` after try 4.
   - A broken job goes straight to `notify.failed`.
   - Replay moves failed jobs back and they get sent.
   - A job that isn't acked (worker stopped mid-job) is handed out again.
   - CI gets a RabbitMQ service and the `parley_test` vhost.
- **Not in this task:** real browser push (T24), merging many messages into one notification (T24 uses one tag per chat so they replace each other), mute settings.
- **Done when:**
  - With three terminals (backend, worker, app): Ana sends to Ben while Ben's tab is closed. About 5 s later the worker logs "notify Ben: New message from Ana".
  - Ben has the chat open and reads it at once: the worker logs "skip: already read".
  - With `NOTIFY_FAKE_FAIL_TIMES=2`: the log shows try 1 failed, try 2 failed, try 3 sent, about 10 s and 1 min apart.
  - With `NOTIFY_FAKE_FAIL_TIMES=10`: the job shows in `notify.failed` on localhost:15672. Set it back to 0 and run replay, and it's sent.
  - Stop the worker, send 3 messages, start the worker: all 3 are handled, none lost.
  - Stop RabbitMQ: chatting still works.
  - All tests pass, CI is green (run link in the report), and "In my words" is filled in by Adithya.

"In my words" prompts: how a job waits 10 s, 1 min or 5 min with no sleeping code (timers on queues, then falling back into `notify`); why the worker acks only at the end, and why that means a job can run twice and how "already notified" stops a double; what `notify.failed` and replay are for, and why a broken job skips the retries.

---

## All tasks

### Phase 0: Setup
- [x] T1. Repo and plan files
- [x] T2. The look: Parley's colors, fonts and logo, plus screen sketches using the reference layout (reference screenshots go in `docs/reference/`)

### Phase 1: Screens with fake data (React)
- [x] T3. Create the React app (Vite + TypeScript) with Tailwind CSS and shadcn/ui, plus a `.gitignore` for `node_modules`. Do it in two steps: Vite + Tailwind first, shadcn/ui after that works
- [x] T4. The main screen with fake data: layout, chat list, conversation, side panel, upload view, phone (T4 to T6 merged)
- ~~T5~~ merged into T4
- ~~T6~~ merged into T4
- [x] T7. Sign-up and log-in screens (not connected yet)

### Phase 2: Backend basics
- [x] T8. FastAPI app with a health check, PostgreSQL in Docker Compose, a first tiny pytest test, and `.gitignore` entries for the Python venv and `.env`
- [x] T9. First tables with SQLAlchemy and Alembic: users, sessions
- [x] T10. Sign up and log in: hashed passwords, short and long passes (tokens)
- [x] T11. GitHub Actions: run the tests on every pull request (CI has no `.env`, so set `DATABASE_URL` and `JWT_SECRET` there and start a Postgres service)
- [x] T12. Connect the sign-up and log-in screens to the real backend (only one refresh at a time per tab, other requests wait for it; if a refresh gets 401, wait a moment and retry once, since another tab may have just rotated the cookie; use a Vite proxy so the cookie works)

### Phase 3: Messages over HTTP
- [x] T13. Chat tables (start the brief with the table map; add the new tables to the conftest TRUNCATE; route tests always use the `client` fixture): chats, chat members, messages (per-chat numbers, message IDs). The brief must explain how two messages sent at the same moment never get the same number (a lock or a counter column)
- [x] T14. Send a message and load history, 30 at a time
- [x] T15. Connect the chat list and conversation screens to real data (check: leave the app open 15+ minutes, then load chats without reloading, to test the 401 → refresh → retry path)

### Phase 4: Live chat (WebSocket)
- [x] T16. WebSocket connection with a one-time ticket (explain the ticket idea on its own first)
- [x] T17. New messages appear instantly; "got it" replies give two ticks (also keep a "Not sent" message in the chat when you switch chats and come back)
- [x] T18. Typing indicator and read ticks
- [x] T19. Reconnect and catch up on missed messages

### Phase 5: Redis
- [x] T20. Online and last seen, with automatic expiry
- [x] T21. Two backend copies; live messages cross between them (pub/sub)
- [x] T22. Spam limits (also decide what happens when Redis is down: today the live line and chat list fail, like when PostgreSQL is down)
- [ ] T22b. Fix: reads and ticks reach the server without the live line (HTTP door for `read` and `delivered`)

### Phase 6: RabbitMQ
- [ ] T23. Notification worker with retries and a failed-jobs queue
- [ ] T24. Browser push notifications (Web Push). Push text must not contain message text (see D12). Web Push needs HTTPS (localhost counts); check again at T26

### Phase 7: Run it like production
- [ ] T25. Dockerfiles and Docker Compose for every part (the worker gets its own container; the backend and worker start only once PostgreSQL, Redis and RabbitMQ are healthy, since the backend can't start while Redis is down)
- [ ] T26. Nginx in front of several backend copies (run uvicorn with --proxy-headers trusting only Nginx, so rate limits see the real IP) (demo: stop one copy mid-chat and the apps reconnect to the other through Nginx, with nothing lost) (turn on `secure=True` for the refresh cookie once HTTPS is on)

### Phase 8: Measure it
- [ ] T26b. Deploy Parley live on one AWS EC2 server: Docker Compose + Nginx + HTTPS (a cheap domain or a free subdomain), refresh cookie `secure=True`. First: set an AWS budget alert (about $10), and check the old delivery-delay Fargate service in ap-southeast-1 is stopped.
- [ ] T27. Prometheus metrics and a Grafana dashboard
- [ ] T28. Load test with 1,000 fake users; write up the results with the laptop's specs (include 1,000 users connecting at once, to check the per-copy subscribe lock from D23)

### Phase 9: Kubernetes
- [ ] T29. Run Parley on local Kubernetes
- [ ] T30. Optional, only if ready before the AWS free plan ends (around mid-December 2026): short EKS run with Terraform, and record a demo. Tear it all down the same day with `terraform destroy` (the cluster costs money every hour)

### Phase 10: Show it
- [ ] T31. README with an architecture diagram, screenshots, a demo video and the load-test results, plus a short "How I built this" section (planned with Claude, coded with Claude Code; Adithya made the decisions, reviewed and tested every change; LEARNING.md shows what he learned)

### Later
- End-to-end encryption phase: 1:1 text, one device, safety numbers (see D12) (chat-list previews then move to the app, since the server can't read the text)
- v2: groups, images and voice notes, reactions, edit and delete, search
- Optional: move notifications into their own service