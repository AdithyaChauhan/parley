# Parley: Decisions

Every big choice and why. Both Claudes read this before suggesting anything.
To change a decision: discuss it in the planning chat, then add a new entry that replaces the old one. Never silently ignore an entry.

---

**D1. Name: Parley**
An old word for a talk between two sides.

**D2. A web app**
It runs in the browser (desktop first) and works on phone browsers. No mobile app.

**D3. How messages travel**
- Sending a message: a normal HTTP request (easy to test, clear success and error codes).
- Everything live (new messages, ticks, typing, online): one WebSocket connection.
- This is the same split Discord and Slack apps use.

**D4. Plain WebSockets, no Socket.IO**
We build reconnecting, "got it" replies and rooms ourselves, because that's what interviewers ask about.

**D5. One app first (a monolith)**
One backend split into clean folders by feature: auth, chats, messages, live.
Later we may move one piece (notifications) into its own service. Each new piece must connect to something that already works.

**D6. Backend: Python + FastAPI**
- Database: PostgreSQL, through SQLAlchemy.
- Database changes: Alembic migrations.
- Tests: pytest.
- Packages: pip with a virtual environment.

**D7. Frontend: React + TypeScript + Vite + Tailwind CSS + shadcn/ui**
Screens are built first with fake data. Then each backend feature plugs into a screen that already exists.
The small packages shadcn/ui installs for itself (for example cn, clsx, tailwind-merge, class-variance-authority, lucide-react icons, tw-animate-css, radix-ui) count as part of shadcn/ui. No dark mode for now. The only font is Outfit from Google Fonts; preset fonts (like Geist) are removed.
ESLint (from Vite's template) checks the code for mistakes. It's a dev-only tool and never ships with the app.
react-router handles page addresses (/login, /signup, /). Added in T12.

**D8. Look (updated)**
Parley matches the reference screenshots closely: layout, colors, spacing, shapes and font style.
The blue-grey frame around the app in the screenshots is only a showcase background. The real app fills the whole browser window, with no outer frame, and resizes with it. Profile areas are kept compact so lists get the most space.
Not copied: the logo, names and photos. Parley has its own logo, made-up names and its own avatars. The README credits the reference design.
Group chats, the side panel and uploads are built as screens first. They work for real in v2.

**D9. Message rules**
- Save to the database before sending anywhere.
- Each message carries an ID made by the sender's app, so a retried send is never saved twice.
- Each chat numbers its messages #1, #2, #3. Apps sort by this number, not by time.
- Ticks come from two bookmarks per chat member: "delivered up to #" and "read up to #".

**D10. Supporting tools (added in this order)**
- Redis: online status and passing messages between backend copies.
- RabbitMQ: notification jobs with retries.
- Docker Compose, then Nginx.
- Prometheus and Grafana.
- Kubernetes on the laptop.
Kafka is not used: RabbitMQ fits our jobs and is lighter.

**D11. AWS later**
Kubernetes runs on the laptop. A short EKS run happens only if ready before the AWS free plan ends (around mid-December 2026).

**D12. Encryption is a later phase**
- 1:1 text only, one device per user, Web Crypto (ECDH + AES-GCM), safety-number check.
- From day one, the server only passes message text along and never reads it: no message text in notifications, no server-side search.

**D13. Git workflow**
- `main` always works.
- One branch per task (`feature/`, `fix/`, `docs/`, `chore/`), merged by pull request.
- Adithya makes every commit and writes the message in his own words. Commits never have a "Co-Authored-By: Claude" line.
- PR descriptions never mention Claude or Claude Code (no "Generated with" line). Credit for how the project was built lives once, in the README's "How I built this" section (T31).
- Private repo; goes public once live chat works.

**D14. Who does what**
- Adithya: final say. Nothing starts or merges without his OK.
- Planning chat (Claude on claude.ai): writes the plan, task briefs and decisions; teaches.
- Claude Code: writes project code, one file at a time. Adithya can write a file himself whenever he wants; he tells Claude Code first. Stops and reports if a brief clashes with the code or with this file.
- Only the planning chat changes PLAN.md and DECISIONS.md. Adithya copies the new versions into the repo.

**D15. Database access style**
- SQLAlchemy 2.x in normal (sync) mode for now: simpler to learn and debug. We revisit async only if load tests (T28) show a need.
- Ids for users and sessions are UUIDs: safe to make anywhere, and not guessable from the URL.
- Config comes from `.env` through pydantic-settings. No secrets in committed files.

**D16. How log-in works**
- Passwords: hashed with argon2 (argon2-cffi). Never stored or logged in plain text.
- Access token: a JWT (PyJWT) that lasts 15 minutes, sent as "Authorization: Bearer".
- Refresh token: random, lasts 7 days, sent in an httpOnly cookie. Only its SHA-256 fingerprint is stored, in `sessions`. Each refresh swaps it for a new one (rotation) in the same `sessions` row and moves the expiry to 7 days from now, so you stay logged in while you keep using the app.
- Emails are checked with pydantic's EmailStr (email-validator), then trimmed and lowercased before saving or looking up.
- Log-in errors never reveal whether an email exists.

**D17. One address for the whole app**
- Every backend route lives under `/api` (for example `/api/auth/login`).
- In development, Vite passes `/api` on to FastAPI (a proxy). Later, Nginx does the same job (T26).
- So the browser sees one site, and the refresh cookie (path `/api/auth`) works without extra cross-site settings.
- Rule for every proof step (like the red-cross test): put the run link or a screenshot in the report.

**D18. How message numbers are kept safe**
- Each chat row holds a counter, `last_seq`. Taking the next number is one `UPDATE ... RETURNING` on that row, which locks it, so two senders never get the same number.
- The database also refuses a second #N in the same chat (unique `chat_id` + `seq`).
- A send carries the sender app's `client_msg_id`; the database refuses a second copy (unique `sender_id` + `client_msg_id`), and the server returns the first one instead.
- A direct chat between two people has a unique `direct_key`, so they can't end up with two direct chats.

**D19. The live connection**
- One WebSocket per open tab, at `/api/live`. The server uses it to push events; sending messages still goes over HTTP (D3).
- Getting on: `POST /api/live/ticket` (with the access token) gives a ticket that works once and dies after 30 seconds. The app opens `/api/live?ticket=...`. A bad ticket closes the line with code 4401.
- Every event is JSON shaped `{"type": "...", "data": {...}}`.
- Tickets live in the server's memory for now and move to Redis in T21. The open lines can't move: each backend copy keeps its own switchboard for the lines it accepted, and Redis pub/sub carries "push this to Ben" between copies (T21).
- New package: `websockets` (gives uvicorn WebSocket support).

**D20. Live events and ticks**
- Server to app: `message.new` (a saved message) and `receipt` (someone's bookmark moved).
- App to server: `delivered`, `read` and `typing`. `delivered` and `read` carry the chat id and the highest number the app has (for `read`: has shown on screen in an open, focused chat). `read` also lifts `delivered`.
- `receipt` carries both bookmarks (`delivered_up_to`, `read_up_to`) and goes to everyone in the chat, including the reader's own other tabs. Unread is always (newest number in the chat) − (my read_up_to). The app uses the higher of the server's read_up_to and what it has already shown, so a badge never comes back while a read is on its way.
- Sending counts as reading: when someone's message is saved as #N, the server moves their own bookmarks to #N without a receipt. So a message from someone at #N also means their bookmarks are at least #N, and the app applies this to pushed messages. History and catch-up pages already carry the real bookmarks.
- Known simplification: in an offline race (both people's waiting messages go out together), this can show "read" a few seconds before the sender actually sees the other message. Accepted.
- `typing` is passed on to the other members and never saved.
- `delivered` and `read` also have an HTTP door: `POST /api/chats/{chat_id}/delivered` and `/read`, body `{"seq": N}` (the same name the live line uses). The reply carries both bookmarks. Bookmarks (kept in PostgreSQL) never depend on Redis. `typing` stays live-only, since an old "typing..." is useless.
- One shared function, `save_bookmark`, serves both doors: it saves the bookmark, then pushes the receipt with the normal Redis client (also when called from the live line's worker thread).
- The app uses the HTTP door only once the line is known to be down (it dropped, or a connect failed, such as a ticket 503). It doesn't use it while the line is first connecting. It sends only what the server hasn't confirmed yet.
- A bookmark that doesn't move pushes no receipt.
- Bookmarks (`delivered_up_to`, `read_up_to`) only move forward and never past the chat's `last_seq`.
- A push that fails never undoes or fails a send; the message is already saved (D9). Missed pushes are made up later (T19 catch-up).

**D21. Reconnect and catch-up**
- The app sends `ping` every 25 s; the server answers `pong`. No `pong` within 10 s means the line is dead.
- Reconnect waits 1, 2, 4 ... up to 30 s, plus a little random extra, and gets a new ticket each time.
- Catch-up uses message numbers, never times: the app asks for `after=<highest number it has with no hole below it>`. A pushed message, or my own send's reply, that skips numbers also triggers a catch-up.
- When the browser reports "offline", the app closes the line itself and reconnects as soon as it reports "online".
- `ping`/`pong` keep D19's shape: `pong` is `{"type":"pong","data":{}}`, and an event with no `data` counts as `{}`.
- Messages sent while offline wait in order and are sent one at a time when the line is back, each with its original `client_msg_id` (no doubles, D18).
- The open chat also catches up when the chat list (re-checked every 60 s) shows a higher message number than it has. So during an outage, Ben sees Ana's message within about a minute with no reload.

**D22. Redis and online status**
- Redis (official image, pinned version) runs in Docker Compose. Python talks to it with the `redis` package: the normal client in normal routes, the async client on the live line.
- Redis holds fast, temporary facts (online status, and later tickets and pub/sub). PostgreSQL stays the only home for anything that must never be lost.
- Online status is per tab: `presence:<user>` is a sorted set of tab id → "alive until" (now + 60 s), refreshed by every ping. Online means at least one tab is still alive. A crashed tab goes offline by itself when its time passes.
- `last_seen:<user>` is updated on every ping and on close.
- Locally, `REDIS_URL` uses `127.0.0.1`, not `localhost` (on Windows, `localhost` costs about 1 s per try when Redis is down).
- Chat rows carry `other_user_id` (empty for groups), so a `presence` event can update just the matching row.
- "Online" is recorded and pushed before `hello` is sent, and the goodbye (`tab_closed` plus the offline push) is shielded for up to 5 s so it finishes even during shutdown.
- Tests use `TEST_REDIS_URL` (database 15), wipe it after each test, and refuse to run on any other.
- The async client opens and closes with the app (startup/shutdown in `main.py`).
- A tab whose time runs out pushes nothing; other apps notice at their next 60 s check, so offline can take up to about 2 minutes after a silent crash.

**D23. Several backend copies (Redis pub/sub)**
- Every push goes through Redis pub/sub: the sender's copy publishes the event on `user:<id>` for each person who should get it, and every copy delivers what it hears to its own open lines.
- A copy listens on `user:<id>` only while that person has a line on it (subscribe on the first line, unsubscribe on the last).
- Pub/sub keeps nothing. A lost event is fine because the message is saved first (D9) and the app catches up by number (D21).
- Tickets live in Redis (`ticket:<t>`, 30 s timer) and are redeemed with `GETDEL`, so any copy can redeem a ticket any copy made, exactly once.
- Each copy has a `COPY_NAME`, shown in `/api/health`.
- Pub/sub ignores Redis database numbers, so dev (db 0) and tests (db 15) share channel names. That's harmless because user ids are random UUIDs.
- Subscribe and unsubscribe on a copy go through one lock. Check it under load in T28.

**D24. Limits, and when Redis is down**
- Limits use a sliding window in Redis (a sorted set of times, one transaction per check). Too many gives 429 with `Retry-After`.
- Sends: 20 per 10 s per user. Wrong passwords: 5 per 15 min per email (cleared by a good log-in; locked emails refuse even the right password until the time passes). Any log-in: 30 per 15 min per IP. Sign-ups: 5 per hour per IP. Start-chat: 20 per minute per user. Tickets: 10 per minute per user.
- Redis is a helper, PostgreSQL is the truth. When Redis is down: sends and history keep working (live pushes are lost and caught up later), online shows as unknown, tickets answer 503, and limits let requests through with a logged warning.
- The app treats 429 on a send like "waiting": it tries again after `Retry-After`, in order.
- Redis clients give up fast: 1 s connect timeout. The normal client tries once. The async (live line) client keeps one quick retry, so lines survive a Redis restart.
- When Redis drops, open live lines close cleanly (code 1011) and the app reconnects with its backoff (D21).
- During a Redis outage, bookmarks still save (HTTP door, D20). While the live line is down, the open chat also asks for `messages?after=<gap-free seq>` every 60 s, in step with the chat list's re-check. That reply carries both bookmarks, so the other person's ticks update within about a minute, and instantly again once the line is back.

**D25. Notifications (RabbitMQ)**
- RabbitMQ carries notification jobs to a separate worker. Python uses `pika`. Jobs carry ids and numbers only, never message text (D12).
- Each job waits 5 s first (`notify.wait`), then is skipped if the recipient has already read it.
- Retries wait 10 s, 1 min, then 5 min, using queues with their own timers that fall back into `notify`. After try 4 the job goes to `notify.failed`. A broken job goes straight there. `replay` sends failed jobs back.
- Delivery is "at least once": the worker acks only after finishing, so a job can run twice. Redis `notified:<message>:<user>` (24 h) stops a double notification. From T24, whoever sends writes the note: `LogNotifier` keeps this per-person note, and `WebPushNotifier` writes one per device (D26).
- Setup: `rabbitmq:4.3.7-management` (4.4.0 was only 3 days old), `pika==1.4.4`. The RabbitMQ user and password come from `.env` (the built-in guest user only works inside the container). It has a named volume and a fixed hostname, so parked jobs survive `docker compose down`. Tests use the `parley_test` vhost only.
- The publisher declares the queues each time it connects (the first send, and after every reconnect), so the backend starts and chats fine with RabbitMQ down. One shared connection behind a lock (wait at most 1 s). After a failed connect, it skips publishing for 10 s and logs it once, so an outage doesn't add 1 s to every send.
- Timers live on the queues: changing one means deleting that queue first (RabbitMQ refuses a different timer, error 406).
- From T24 the notifier's shape is `send(job, user_name, title)`. It returns what happened: "sent", "skip: no devices" or "skip: already notified". The worker no longer touches the notes. A job whose message or member is gone is skipped, not retried.
- Health check: `rabbitmq-diagnostics -q check_port_connectivity` (not `ping`, which passes while RabbitMQ is still booting). Wait for "healthy" before using `rabbitmqctl` (about 11 s after "Up").
- One `queues.send_job()` (persistent, confirmed) is used by the publisher, the worker and replay. Only a connection error starts the 10 s skip. Other errors (like a 406) are logged with the real reason, and the send still gives 201.
- If the "notified" note can't be written after a successful send, the worker logs a warning and doesn't retry (a retry would notify twice). Replay moves only the jobs parked when it starts, so a broken job can't loop.
- The send never waits on RabbitMQ: if publishing fails, the message is still saved and returned, and that notification is lost. Accepted for now. The full fix (an outbox table written in the same transaction as the message) is a known next step.

**D26. Browser notifications (Web Push)**
- Web Push with VAPID keys (`pywebpush`). The private key lives only in `.env`. The app gets the public key from `GET /api/push/key`.
- `push_subscriptions`: one row per browser per user, `endpoint` unique. Subscribing again from the same browser moves the row to the current user. Logging out unsubscribes and deletes the row first.
- The payload is the title ("New message from <name>") and `chat_id` only, never message text (D12), with a TTL of 1 hour. The service worker uses `tag = chat_id`, so one chat shows one notification.
- The "already sent" note is per device (`notified:<message>:<subscription>`), so a retry only tries the devices that failed.
- 404/410 from the push service means the device is gone: delete the row, no retry. 429, 5xx or a timeout: retry (D25).
- The app asks for permission only when the user clicks "Turn on notifications", never on page load.
- `pywebpush==2.5.0`. The helpers it installs (requests, aiohttp, py-vapid, http-ece) count as part of it. Each push has a 10 s time limit.
- Setting `NOTIFIER` picks the notifier: `log` by default (tests, CI) and `webpush` in `.env`. VAPID settings start empty: `GET /api/push/key` answers 503 without a key, and the worker refuses to start with `webpush` and no keys. Tests make throwaway keys.
- Push service answers: only 404/410 is final (delete the device). Everything else retries and is parked after try 4: connection errors, timeouts, 429, 5xx and other 4xx like a wrong VAPID key (403). So after fixing `.env`, replay sends the parked ones.
- The app re-sends a subscription the browser already has after log-in, but never creates one without the click.
- Known gaps, accepted:
  - If a session just runs out (no log-out click), that browser's row stays until the next log-in there moves it.
  - If Redis fails right after one device got the push and another device failed, the retry can notify the first device twice. Logged as a warning.
- Added in T24 (approved):
  - `sw.js` closes the chat's old notification before showing the new one (same tag). On Windows, a silent replace hid new messages. It's still one notification per chat, but each new message pops up.
  - `sw.js` calls `skipWaiting()`, so a new version takes over at once.
  - Endpoints must start with `https://` (max 2048), because the worker POSTs to an address a user gave us. Allowing only known push-service hosts is a later hardening step.
  - Microsoft's push service answers 401 for a wrong VAPID key. It's covered by "other 4xx retries, then parks".

**D27. Containers**
- One backend image runs three ways: `backend` (uvicorn), `worker` and `migrate` (a one-shot `alembic upgrade head` that the others wait for, so two copies never migrate at once).
- The app is built by Node and served by Nginx (`web`). Nginx passes `/api` and the live line to the backend. From T25, the address is http://localhost:8080.
- `docker compose up` starts only the helpers (dev). `docker compose --profile app up` starts all of Parley.
- `.env` never goes into an image. Images run as non-root, and base images are pinned to exact tags. That includes `postgres` (an exact 17.x patch, since patches keep the same data format).
- Version rule: a brand-new minor or major version (like RabbitMQ 4.4.0) waits a few weeks. A patch release (like 3.13.17) is taken at once, since patches are bug and security fixes. T25 uses `python:3.13.17-slim-trixie`, `node:24.22.1-alpine` and `nginx:1.30.6-alpine`.
- Inside the network, services are reached by their Compose names: `db`, `redis`, `rabbitmq`, `backend`. Compose builds the addresses from the `POSTGRES_*` and `RABBITMQ_*` values in `.env`, so those passwords use only letters and numbers (`@`, `:` or `/` would break the address).
- In a container the worker is PID 1, so it sets its own SIGTERM handler, which takes the same path as Ctrl+C.
- Real IP: Nginx overwrites `X-Forwarded-For` with `$remote_addr`, and uvicorn trusts forwarded headers because the backend port is only reachable inside Parley's network.
- Nginx looks up container names again every 10 s (`resolver 127.0.0.11 valid=10s`), so a new backend container with a new address is found without restarting Nginx.
- Worker and web have no health check, since nothing waits on them. The CI containers job builds, starts and checks the whole stack.

**D28. Several copies behind Nginx**
- Two backend copies (`backend_a`, `backend_b`) run the same image, and differ only in `COPY_NAME`. `migrate` still runs once, first.
- Nginx: `upstream` with `least_conn`, and a dead copy is skipped for 10 s (`max_fails=1 fail_timeout=10s`). Upstream servers use `resolve` with a shared `zone` (free Nginx since 1.27.3), so names are re-checked and Nginx starts even if a copy is missing. This replaces T25's `set $backend` trick. A short connect timeout is used. A POST that never reached a copy (connect failed) is tried on the other one.
- The refresh cookie is set and deleted with the same settings, including `Secure`.
- No sticky sessions: nothing about a user lives in one copy's memory (tickets, pushes, presence and limits are in Redis, data in PostgreSQL), so any request or live line can go to any copy.
- Nginx retries only requests that are safe to repeat. A POST is never retried once sent (token rotation could clash). Message sends are safe anyway through the app's re-send with the same `client_msg_id`.
- A stopping copy closes its live lines at once with code 1012 ("server restarting", which uvicorn already sends on SIGTERM), so apps move to the other copy within seconds.
- `hello` carries the copy name, logged in the browser console for demos.
- `COOKIE_SECURE` (default `false`) sets the refresh cookie's `Secure` flag. It's turned on with HTTPS in T26b.