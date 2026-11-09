# Parley: Decisions

Every big choice and why. Both Claudes read this before suggesting anything.
To change a decision: discuss it in the planning chat, then add a new entry that replaces the old one. Never silently ignore an entry.

---

### D1. Name: Parley
An old word for a talk between two sides.

### D2. A web app
It runs in the browser (desktop first) and works on phone browsers. No mobile app.

### D3. How messages travel
- Sending a message: a normal HTTP request (easy to test, clear success and error codes).
- Everything live (new messages, ticks, typing, online): one WebSocket connection.
- This is the same split Discord and Slack apps use.

### D4. Plain WebSockets, no Socket.IO
We build reconnecting, "got it" replies and rooms ourselves, because that's what interviewers ask about.

### D5. One app first (a monolith)
One backend split into clean folders by feature: auth, chats, messages, live.
Later we may move one piece (notifications) into its own service. Each new piece must connect to something that already works.

### D6. Backend: Python + FastAPI
- Database: PostgreSQL, through SQLAlchemy.
- Database changes: Alembic migrations.
- Tests: pytest.
- Packages: pip with a virtual environment.

### D7. Frontend: React + TypeScript + Vite + Tailwind CSS + shadcn/ui
Screens are built first with fake data. Then each backend feature plugs into a screen that already exists.
The small packages shadcn/ui installs for itself (for example cn, clsx, tailwind-merge, class-variance-authority, lucide-react icons, tw-animate-css, radix-ui) count as part of shadcn/ui. No dark mode for now. The only font is Outfit from Google Fonts; preset fonts (like Geist) are removed.
ESLint (from Vite's template) checks the code for mistakes. It's a dev-only tool and never ships with the app.
react-router handles page addresses (/login, /signup, /). Added in T12.

### D8. Look (updated)
Parley matches the reference screenshots closely: layout, colors, spacing, shapes and font style.
The blue-grey frame around the app in the screenshots is only a showcase background. The real app fills the whole browser window, with no outer frame, and resizes with it. Profile areas are kept compact so lists get the most space.
Not copied: the logo, names and photos. Parley has its own logo, made-up names and its own avatars. The README credits the reference design: "KeyVue chat" by Karol Kos for widelab, on Dribbble.
Group chats, the side panel and uploads are built as screens first. They work for real in v2.
Window sizes (T27):
- From 1280 px, all four columns show: rail, list, chat and side panel. The panel can fold to a thin strip that shows only the open button and the avatar.
- At 768-1279 px, the side panel has no column. Tapping the name at the top of the chat shows the panel in the chat's place, with a back arrow, and the chat list stays.
- Under 768 px, it's one screen at a time (list, chat, files), with a back arrow only and no "Chat" or "Shared files" titles. There's no bottom bar: with only Chats left, it would be one button that does nothing.
- The rail (from 768 px) holds the logo, the Chats icon right under it, and the user's avatar at the bottom.
- "Reconnecting..." shows under the user's name only while the live line is down. The list moving down a little during a reconnect is accepted.
No dead buttons on the live app. Anything that doesn't work yet is hidden, not shown as "coming soon". That covers:
- the rail icons other than Chats
- the "available" pill
- the "..." menu
- emoji and attach, and file drop
- the "Messages" and "Participants" tabs (in v2, a group's members show in the side panel, reached by tapping the name, like WhatsApp's group info)
A hidden button comes back only in the task that makes it work: attach and drop with files, emoji with reactions, the "..." menu with groups (all v2). The eye icon comes back with Status and the calls icon with calls (maybe later). Dashboard, Tasks and Stats came from the reference design, not WhatsApp, so they stay gone.
Phone keyboard (PR #29): like WhatsApp, the chat header stays at the top and the message box sits just above the keyboard (or at the bottom when it's closed). The page is locked while the chat screen shows (no scroll, no bounce), and only the lists scroll. Text boxes are at least 16 px on phones (iOS zooms smaller ones). Sending jumps to the newest message, and a new message doesn't pull you down if you've scrolled up. There's no pull-to-refresh (live chat doesn't need it). No installable app (PWA) for now, since people open the link in a browser.
The fake file numbers are removed (T27). Every chat's side panel shows "No files yet" until v2. In a 1:1 chat, the side panel shows "online" or "last seen", not "2 members".

### D9. Message rules
- Save to the database before sending anywhere.
- Each message carries an ID made by the sender's app, so a retried send is never saved twice.
- Each chat numbers its messages #1, #2, #3. Apps sort by this number, not by time.
- Ticks come from two bookmarks per chat member: "delivered up to #" and "read up to #".

### D10. Supporting tools (added in this order)
- Redis: online status and passing messages between backend copies.
- RabbitMQ: notification jobs with retries.
- Docker Compose, then Nginx.
- Prometheus and Grafana.
- Kubernetes on the laptop.
Kafka is not used: RabbitMQ fits our jobs and is lighter.

### D11. AWS later
Kubernetes runs on the laptop. A short EKS run happens only if ready before the AWS free plan ends (Feb 2, 2027, or when the credits run out).

### D12. Encryption is a later phase
- 1:1 text only, one device per user, Web Crypto (ECDH + AES-GCM), safety-number check.
- From day one, the server only passes message text along and never reads it: no message text in notifications, no server-side search.

### D13. Git workflow
- `main` always works.
- One branch per task (`feature/`, `fix/`, `docs/`, `chore/`), merged by pull request.
- Adithya makes every commit. From build mode (D14), Claude Code drafts the message. Commits never have a "Co-Authored-By: Claude" line.
- PR descriptions never mention Claude or Claude Code (no "Generated with" line). Credit for how the project was built lives once, in the README's "How I built this" section (T34).
- Private repo; goes public once live chat works.

### D14. Who does what
- Adithya: final say. Nothing starts or merges without his OK.
- Planning chat (Claude on claude.ai): writes the plan, task briefs and decisions.
- Claude Code (build mode from Nov 4, 2026): builds, checks and writes up each task end to end, including a draft "In my words". It decides small clashes itself and lists them in its report. It stops only for money, AWS changes, deleting data, security trade-offs, going against a D-entry, or anything that can't be undone. It never commits, pushes or merges. Adithya can write a file himself whenever he wants.
- Only the planning chat changes PLAN.md and DECISIONS.md. Adithya copies the new versions into the repo.

### D15. Database access style
- SQLAlchemy 2.x in normal (sync) mode for now: simpler to learn and debug. We revisit async only if load tests (T31) show a need. Revisited after T31 (D34): not needed, since the limit is CPU (about one core per copy), which async wouldn't lift.
- Ids for users and sessions are UUIDs: safe to make anywhere, and not guessable from the URL.
- Config comes from `.env` through pydantic-settings. No secrets in committed files.

### D16. How log-in works
- Passwords: hashed with argon2 (argon2-cffi). Never stored or logged in plain text.
- Access token: a JWT (PyJWT) that lasts 15 minutes, sent as "Authorization: Bearer".
- Refresh token: random, lasts 7 days, sent in an httpOnly cookie. Only its SHA-256 fingerprint is stored, in `sessions`. Each refresh swaps it for a new one (rotation) in the same `sessions` row and moves the expiry to 7 days from now, so you stay logged in while you keep using the app.
- Emails are checked with pydantic's EmailStr (email-validator), then trimmed and lowercased before saving or looking up.
- Log-in errors never reveal whether an email exists.

### D17. One address for the whole app
- Every backend route lives under `/api` (for example `/api/auth/login`).
- In development, Vite passes `/api` on to FastAPI (a proxy). Later, Nginx does the same job (T26).
- So the browser sees one site, and the refresh cookie (path `/api/auth`) works without extra cross-site settings.
- Rule for every proof step (like the red-cross test): put the run link or a screenshot in the report.

### D18. How message numbers are kept safe
- Each chat row holds a counter, `last_seq`. Taking the next number is one `UPDATE ... RETURNING` on that row, which locks it, so two senders never get the same number.
- The database also refuses a second #N in the same chat (unique `chat_id` + `seq`).
- A send carries the sender app's `client_msg_id`; the database refuses a second copy (unique `sender_id` + `client_msg_id`), and the server returns the first one instead.
- A direct chat between two people has a unique `direct_key`, so they can't end up with two direct chats.

### D19. The live connection
- One WebSocket per open tab, at `/api/live`. The server uses it to push events; sending messages still goes over HTTP (D3).
- Getting on: `POST /api/live/ticket` (with the access token) gives a ticket that works once and dies after 30 seconds. The app opens `/api/live?ticket=...`. A bad ticket closes the line with code 4401.
- Every event is JSON shaped `{"type": "...", "data": {...}}`.
- Tickets live in the server's memory for now and move to Redis in T21. The open lines can't move: each backend copy keeps its own switchboard for the lines it accepted, and Redis pub/sub carries "push this to Ben" between copies (T21).
- New package: `websockets` (gives uvicorn WebSocket support).

### D20. Live events and ticks
- Server to app: `message.new` (a saved message) and `receipt` (someone's bookmark moved).
- App to server: `delivered`, `read` and `typing`. `delivered` and `read` carry the chat id and the highest number the app has (for `read`: has shown on screen in an open, focused chat). `read` also lifts `delivered`.
- `receipt` carries both bookmarks (`delivered_up_to`, `read_up_to`) and goes to everyone in the chat, including the reader's own other tabs. Unread is always (newest number in the chat) − (my read_up_to). (From T37, unread counts only real messages: D39.) The app uses the higher of the server's read_up_to and what it has already shown, so a badge never comes back while a read is on its way.
- Sending counts as reading: when someone's message is saved as #N, the server moves their own bookmarks to #N without a receipt. So a message from someone at #N also means their bookmarks are at least #N, and the app applies this to pushed messages. History and catch-up pages already carry the real bookmarks.
- Known simplification: in an offline race (both people's waiting messages go out together), this can show "read" a few seconds before the sender actually sees the other message. Accepted.
- `typing` is passed on to the other members and never saved.
- `delivered` and `read` also have an HTTP door: `POST /api/chats/{chat_id}/delivered` and `/read`, body `{"seq": N}` (the same name the live line uses). The reply carries both bookmarks. Bookmarks (kept in PostgreSQL) never depend on Redis. `typing` stays live-only, since an old "typing..." is useless.
- One shared function, `save_bookmark`, serves both doors: it saves the bookmark, then pushes the receipt with the normal Redis client (also when called from the live line's worker thread).
- The app uses the HTTP door only once the line is known to be down (it dropped, or a connect failed, such as a ticket 503). It doesn't use it while the line is first connecting. It sends only what the server hasn't confirmed yet.
- A bookmark that doesn't move pushes no receipt.
- From T35, the app sends `delivered` and `read` at most once a second per chat, always with the highest number, so a busy chat doesn't write a bookmark for every message.
- Bookmarks (`delivered_up_to`, `read_up_to`) only move forward and never past the chat's `last_seq`.
- A push that fails never undoes or fails a send; the message is already saved (D9). Missed pushes are made up later (T19 catch-up).

### D21. Reconnect and catch-up
- The app sends `ping` every 25 s; the server answers `pong`. No `pong` within 10 s means the line is dead.
- Reconnect waits 1, 2, 4 ... up to 30 s, plus a little random extra, and gets a new ticket each time.
- Catch-up uses message numbers, never times: the app asks for `after=<highest number it has with no hole below it>`. A pushed message, or my own send's reply, that skips numbers also triggers a catch-up.
- When the browser reports "offline", the app closes the line itself and reconnects as soon as it reports "online".
- `ping`/`pong` keep D19's shape: `pong` is `{"type":"pong","data":{}}`, and an event with no `data` counts as `{}`.
- Messages sent while offline wait in order and are sent one at a time when the line is back, each with its original `client_msg_id` (no doubles, D18).
- The open chat also catches up when the chat list (re-checked every 60 s) shows a higher message number than it has. So during an outage, Ben sees Ana's message within about a minute with no reload.

### D22. Redis and online status
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

### D23. Several backend copies (Redis pub/sub)
- Every push goes through Redis pub/sub: the sender's copy publishes the event on `user:<id>` for each person who should get it, and every copy delivers what it hears to its own open lines.
- A copy listens on `user:<id>` only while that person has a line on it (subscribe on the first line, unsubscribe on the last).
- Pub/sub keeps nothing. A lost event is fine because the message is saved first (D9) and the app catches up by number (D21).
- Tickets live in Redis (`ticket:<t>`, 30 s timer) and are redeemed with `GETDEL`, so any copy can redeem a ticket any copy made, exactly once.
- Each copy has a `COPY_NAME`, shown in `/api/health`.
- Pub/sub ignores Redis database numbers, so dev (db 0) and tests (db 15) share channel names. That's harmless because user ids are random UUIDs.
- Subscribe and unsubscribe on a copy go through one lock. Check it under load in T31.

### D24. Limits, and when Redis is down
- Limits use a sliding window in Redis (a sorted set of times, one transaction per check). Too many gives 429 with `Retry-After`.
- Sends: 20 per 10 s per user. Wrong passwords: 5 per 15 min per email (cleared by a good log-in; locked emails refuse even the right password until the time passes). Any log-in: 30 per 15 min per IP. Sign-ups: 5 per hour per IP. Start-chat: 20 per minute per user. Tickets: 10 per minute per user.
- Redis is a helper, PostgreSQL is the truth. When Redis is down: sends and history keep working (live pushes are lost and caught up later), online shows as unknown, tickets answer 503, and limits let requests through with a logged warning.
- The app treats 429 on a send like "waiting": it tries again after `Retry-After`, in order.
- Redis clients give up fast: 1 s connect timeout. The normal client tries once. The async (live line) client keeps one quick retry, so lines survive a Redis restart.
- When Redis drops, open live lines close cleanly (code 1011) and the app reconnects with its backoff (D21).
- During a Redis outage, bookmarks still save (HTTP door, D20). While the live line is down, the open chat also asks for `messages?after=<gap-free seq>` every 60 s, in step with the chat list's re-check. That reply carries both bookmarks, so the other person's ticks update within about a minute, and instantly again once the line is back.

### D25. Notifications (RabbitMQ)
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

### D26. Browser notifications (Web Push)
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

### D27. Containers
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
- Health checks that start a heavy program (an Erlang VM for RabbitMQ, Python for the backends) run every 30 s once a container is up, and faster (`start_interval`) while it's starting. At 5 s they took ~19% of the server's CPU (T29 follow-up). Light checks (`pg_isready`, `redis-cli ping`) may stay at 5 s.

### D28. Several copies behind Nginx
- Two backend copies (`backend_a`, `backend_b`) run the same image, and differ only in `COPY_NAME`. `migrate` still runs once, first.
- Nginx: `upstream` with `least_conn`, and a dead copy is skipped for 10 s (`max_fails=1 fail_timeout=10s`). Upstream servers use `resolve` with a shared `zone` (free Nginx since 1.27.3), so names are re-checked and Nginx starts even if a copy is missing. This replaces T25's `set $backend` trick. A short connect timeout is used. A POST that never reached a copy (connect failed) is tried on the other one.
- The refresh cookie is set and deleted with the same settings, including `Secure`.
- No sticky sessions: nothing about a user lives in one copy's memory (tickets, pushes, presence and limits are in Redis, data in PostgreSQL), so any request or live line can go to any copy.
- Nginx retries only requests that are safe to repeat. A POST is never retried once sent (token rotation could clash). Message sends are safe anyway through the app's re-send with the same `client_msg_id`.
- A stopping copy closes its live lines at once with code 1012 ("server restarting", which uvicorn already sends on SIGTERM), so apps move to the other copy within seconds.
- `hello` carries the copy name, logged in the browser console for demos.
- `COOKIE_SECURE` (default `false`) sets the refresh cookie's `Secure` flag. It's turned on with HTTPS in T28.
- Known behaviour: for a stopped container, Docker's name service answers "server failure", not "no such name", so Nginx keeps the old address. While a copy stays down, about one request in 10 s waits the 2 s connect timeout, then goes to the other copy, with no errors. Active health checks come with a cloud load balancer or Kubernetes (T32/T33).
- After renaming a Compose service, use `up --remove-orphans` to remove the old container.
- `up -d --build web` also recreates the backend copies (they're its dependencies). For a frontend-only change, use `up -d --no-deps --build web`, so live lines don't drop.

### D29. AWS is optional, never required
- Parley must always run with no AWS at all: `docker compose --profile app up` on any machine (a laptop or any Linux server) is the main way to run it, and it keeps working after the AWS free plan ends.
- The app code has no AWS SDK and no AWS-only features. It reads plain settings (database, Redis and RabbitMQ addresses, secrets) from the environment, the same on a laptop and on AWS.
- Everything AWS-specific lives in `deploy/aws/` (Terraform, deploy workflow, notes). Deleting that folder, or running `terraform destroy`, never breaks the project.
- File storage (v2) uses the S3 protocol: a self-hosted store in Docker Compose by default, and AWS S3 only when configured. It's the same code either way. (MinIO was the first pick; D38 replaces it.)
- When the free plan ends: `terraform destroy` the same day, keep the README's demo video and screenshots as proof, and the project still runs locally with one command.

### D30. Going live (T28, T29)
- The account is on AWS's credit-based free plan: credits (about $141 as of Oct 28, 2026) and access until Feb 2, 2027. Running costs come out of those credits, so the brief's cost estimates are in credits used per month.
- Region `ap-south-1` (Mumbai). One EC2 server (Ubuntu LTS, x86, sized from `docker stats`, plus 2 GB swap) with an Elastic IP, built by Terraform in `deploy/aws/terraform/`. Every resource is tagged `project=parley`.
- No SSH: the security group opens only 80 and 443. Shell access is through AWS Session Manager (an instance role with `AmazonSSMManagedInstanceCore`).
- The Terraform state stays local and gitignored for now (one person, one server). Moving it to S3 is a later step if more people join.
- Claude Code never runs `terraform apply` or `destroy`, or any other AWS change, without Adithya's OK on the plan.
- The server setup is generic (D29): `docker-compose.prod.yml` and `deploy/server/` run Parley on any Linux server. On a server, db, Redis and RabbitMQ have no published ports, and only Nginx is reachable.
- HTTPS: a Let's Encrypt certificate through certbot (`v5.8.0`): the first one with `first-cert.sh` (standalone), then renewed automatically through webroot. Port 80 only serves the check and redirects to https. The domain is a free DuckDNS subdomain for now.
- Production has its own secrets, including its own VAPID keys. They're typed on the server and never pass through a chat. `COOKIE_SECURE=true` on the server.
- Before the repo goes public, its whole history is scanned for secrets.
- Agreed at the T28 pre-check:
  - Server: t3.small (2 GB) plus 2 GB swap, `cpu_credits = "standard"` (it slows down instead of billing extra), and Ubuntu 24.04 LTS, with image updates ignored after the first build. That's about $22/month in credits (server $16.35, Elastic IP $3.65, 20 GB gp3 $1.82), roughly $70 until Feb 2.
  - Terraform builds its own small network (VPC, public subnet, internet gateway, route table), since Mumbai has no default VPC. `destroy` removes it all.
  - Nginx stays non-root (D27): it listens on 8080 and 8443 inside the container, and the server maps 80 → 8080 and 443 → 8443. A certbot deploy hook gives Nginx's group read access to the key after every new or renewed certificate.
  - The first certificate comes from `first-cert.sh` (certbot standalone on port 80 for about 30 s, before Nginx starts). Renewals use webroot through Nginx, with a dry run to prove it works.
  - `migrate` has no restart rule (it's a one-shot job). Every other service gets `restart: unless-stopped`.
  - Production `JWT_SECRET` and VAPID keys are generated on the server, so they never leave it. No DuckDNS token is stored: the fixed IP is set once on duckdns.org.
  - The repo was scanned (gitleaks over all branches and PR refs, plus the real `.env` values) and is clean, so it can go public.
  - Terraform `1.16.x` (installed: 1.16.6). Per D27's version rule, we stay on 1.16 for now, since 1.17 is a new minor version.
  - The budget alert is $30/month (80% actual, 100% forecast, 100% actual). It excludes credits, so it counts real usage and fires on Parley's ~$22 only if something extra runs. Credits as of Oct 30: $140.52.
- After T28 (done Oct 31, 2026): live at https://parley-adithya.duckdns.org (Elastic IP 16.4.0.127). The server runs `main` from `/opt/parley` (from T29: an exact commit of `main`, set by each deploy, D31). HSTS is on for one year, without `preload` (the DuckDNS name may be dropped after Feb).
- Deploying: `bash deploy/server/deploy.sh` (full) or `deploy.sh web` (frontend only). `web` is always recreated, because a single-file mount keeps the old `nginx.prod.conf` after `git pull`. Known: a full deploy can restart both backend copies together, so live lines reconnect within seconds (nothing is lost). T29 restarts them one at a time.
- Off switch: `terraform destroy` (11 resources), not "stop" (a stopped server still costs ~$5.50/month for the disk and IP). Afterwards, clear the IP on duckdns.org.
- Known gaps: no backups (the database lives on the one disk), and images are built on the server (T29 moves builds to CI).

### D31. Auto-deploy (T29)
- GitHub Actions deploys `main` after CI passes: images are built in CI, tagged with the commit, pushed to ECR (keep the last 10), and the server is told to update through SSM (no SSH). It can also be run by hand with an older tag, which is the rollback.
- GitHub reaches AWS through OIDC: a role that only `AdithyaChauhan/parley` on `main` can use, allowed only to push to the two ECR repositories and to send commands to this one server. GitHub stores no AWS keys, only variables.
- Production secrets live in SSM Parameter Store (SecureString, `/parley/prod/*`). The server's role reads them and writes `.env` (600) on each deploy. Locally and on any other server, a plain `.env` still works (D29).
- Deploys restart the backend copies one at a time (wait for healthy in between), so live lines move to the other copy and nothing is lost.
- `/api/health` shows the running version (the commit).
- CloudWatch: container logs (7-day retention), and an alarm on the server's status checks and high CPU, sending an email through SNS.
- `deploy/server/deploy.sh` refuses to run outside `${PARLEY_DIR:-/opt/parley}` (setup.sh allows another folder on generic servers).
- Agreed at the T29 pre-check:
  - The account already has a GitHub OIDC provider (made for the old delivery-delay project). Parley's Terraform only **reads** it (a data source) and owns just its own role, so `destroy` never deletes something shared. If the delivery-delay leftovers are cleaned up, delete its role, not the provider.
  - Storing the secrets needs write access once: a Terraform variable switches on "write /parley/prod/*" for the server role, the secrets are stored, then a second apply removes it.
  - The AWS CLI on the server comes from `sudo snap install aws-cli --classic` (one time). The scripts stop with a clear message if it's missing.
  - GitHub may run only Parley's own SSM document, `parley-deploy`, on only this server. It takes only a version tag (7-40 hex characters) and runs only the deploy. It can't run any other command, so it can't read the secrets.
  - Each deploy checks out the exact commit (`git checkout --detach <commit>`, as ssm-user), so a rollback also rolls back the Compose files, `nginx.prod.conf` and the scripts. On the AWS server, the workflow is how you deploy. `deploy/server/deploy.sh` there stops with "this server is deployed by GitHub Actions" when it finds a detached commit.
  - `web` is recreated only when `frontend/` or `deploy/server/nginx.prod.conf` changed. `web` stops with SIGTERM (Nginx's fast shutdown), so it doesn't wait 10 s for open live lines. They reconnect anyway (D21). Measure the blip before and after.
  - Rolling restart: after `backend_a` is healthy, wait 15 s (Nginx re-checks names every 10 s, D28) before restarting `backend_b`.
  - Table changes in two steps from now on (expand, then contract): add new columns or tables in one deploy, and remove old ones in a later deploy, because the old copy runs for a moment on the new tables.
  - Only Parley's own containers (backend_a, backend_b, worker, web, migrate) send logs to CloudWatch, set in the AWS-only Compose file. The helpers keep local logs, so the first deploy doesn't restart Redis.
  - The only new GitHub Action is `aws-actions/configure-aws-credentials`, pinned to a version a few weeks old (D27). Building, pushing and SSM use plain `docker` and `aws` commands.
  - ECR tags are immutable (a version can't be overwritten), with basic scan on push. `deploy.yml` uses a concurrency group, so two deploys never overlap.
  - The deploy starts on `workflow_run` after CI on `main` passes, and checks out the exact commit CI tested.
  - The alarm email lives in a gitignored `terraform.tfvars` (the repo is public). `*.tfvars` goes in `.gitignore`.
- Learned while building T29:
  - GitHub's OIDC subject for this repo uses the immutable-id format (`repo:AdithyaChauhan@<owner id>/parley@<repo id>:ref:refs/heads/main`). The trust rule matches it exactly, so a new repo with the same name can't deploy.
  - The GitHub role can also **read** images in the two repositories, because Docker checks whether an image exists before pushing it.
  - The live check after a deploy is "the new version on every answer", not "answers from both copies".
  - The rollback input ignores spaces. The AWS server sits on a detached commit, where `deploy.sh` refuses to run.
  - The ECR login token (12 h) sits in ssm-user's Docker config on the server. That's accepted (host-only, short-lived).
  - Runners are pinned to `ubuntu-24.04`, the same as the server.
  - The old delivery-delay roles stay on purpose (that project continues). They're narrow, limited to that repo's main.
  - T29 finished Nov 1, 2026 (PRs #30 to #33). Every merge to `main` deploys, rolling, with a green live check. The web stop is ~0.2 s with SIGTERM (it was 10.3 s).

### D32. Metrics (T30)
- Prometheus scrapes every part every 15 s and keeps 7 days. Grafana draws one dashboard. Both live in Compose under the `monitoring` profile, with pinned images, and the data source and dashboard are files in the repo.
- The backend uses the official `prometheus-client` with our own small middleware. Routes are labelled by template, never by real ids. `/metrics` is on the app port, and Nginx never passes it on (only `/api/`).
- The worker serves its own metrics on port 9100. The helpers use exporters (Postgres, Redis), RabbitMQ's built-in metrics, and cAdvisor for CPU and memory per container.
- Nothing is opened to the internet. On the laptop, Grafana is on `127.0.0.1:3000`. On the server, only through Session Manager port forwarding, if memory allows (decided in T30).
- Agreed at the T30 pre-check:
  - `GRAFANA_ADMIN_PASSWORD` may be blank in Compose (so the server's deploys, which don't have it, keep working), but Grafana's start command refuses to start without one and says why. That means never admin/admin.
  - One worker counter, `notify_jobs_total{outcome}`: `sent`, the 4 skips, `failed` (a retry was booked) and `parked`. The panel adds up, with no separate retries counter.
  - The Postgres exporter uses the app's user on the laptop. If the dashboard goes on the server (step 6), it first gets its own read-only user (`pg_monitor`).
  - Route labels use FastAPI's real templates (like `/api/chats/{chat_id}/messages`), unknown addresses share one `unmatched` label, `/metrics` doesn't count itself, and Prometheus adds the `copy` label.
  - Queue depth per queue comes from RabbitMQ's detailed metrics page (`queue_coarse_metrics`), with no RabbitMQ changes.
  - cAdvisor comes from `ghcr.io/google/cadvisor` and needs read-only access to the whole machine. That's fine on the laptop, and gets weighed in step 6.
- Decided in T30 (measured): the server runs only the `/metrics` pages, reachable only inside its network. The monitoring stack (550 to 830 MB, mostly Grafana) doesn't fit next to Parley on the t3.small (about 1 GB free) without swapping, and a bigger server (~$16/month more) isn't worth it for a dashboard. The dashboard runs on the laptop, where the load test runs too (T31). T30 finished Nov 1, 2026 (PR #35).

### D33. Load test (T31)
- k6 in Docker (pinned), with scripts in `loadtest/`. It writes its numbers into Prometheus, so they show on the T30 dashboard. It runs on the laptop against the laptop stack, never against the live server.
- The load test uses its own database (`parley_load`), seeded directly (500 pairs, one shared password hash). The seed script refuses any database whose name doesn't end in `_load`.
- `RATE_LIMITS_ENABLED` (default on) may be switched off only for the load test. The app refuses to start with limits off when `COOKIE_SECURE` is true, so production always has its limits (D24).
- The key number is end-to-end latency (send → the partner's live line receives it), measured with p50/p95/p99, plus lost messages (must be 0). "The limit" means p95 end to end over 500 ms or errors over 1%.
- Agreed at the T31 pre-check:
  - Laptop: Acer Aspire 7, Ryzen 5 3550H (4 cores / 8 threads), 8 GB RAM (5.9 GB usable), NVMe SSD, Docker Desktop on WSL2. For the runs, WSL gets 3.5 GB through `.wslconfig` (it was 2.8 GB), other apps are closed, and swap is watched on the dashboard and written down.
  - Laptop memory: WSL gets `memory=3584MB` in `.wslconfig` (whole MB: "3.5GB" with a decimal was ignored). Docker then sees ~3.4 GB.
  - Fake users start **from a saved session**, like opening Parley while already logged in. The seed also creates one session per user with a made-up refresh token (only its fingerprint goes in the database, D16, and only in `parley_load`). The raw tokens go in a gitignored file that k6 reads and that is never committed. Each fake user trades its token at `/api/auth/refresh` (no argon2), about 50 per second, so 1,000 are ready in ~20 s. Every scenario still ends within ~13 min (the access token lasts 15 min, D16).
  - Real logins are measured separately by `loadtest/logins.js` (a short ramp: 2, 3, 4, 6 logins/s), with their own table in `docs/load-test.md`. Measured in the pre-check: fine up to ~4/s (p95 ~300-420 ms). At 6/s it collapses (p95 26 s, backends ~900 MB each, swap), and at 10/s nothing finishes, and the backends keep working on requests nobody waits for. That's the argon2 memory problem.
  - Fake users send `read` for each message they get (both people have the chat open).
  - The load test uses Redis database 1 (presence keys stay out of dev's database 0) and shares RabbitMQ's `/` vhost (load users have no push devices, so their jobs are skipped).
  - The subscribe lock (D23) is judged from k6's "line open → hello" time, and a timer is added only if that's slow.
  - k6's small result files are committed in `loadtest/results/` as proof (checked for tokens first).
  - `loadtest/compose.loadtest.yml` switches only the backend copies, worker and migrate to `parley_load` with limits off, and adds k6. The run script puts the normal backends back after every run. Prometheus gets `--web.enable-remote-write-receiver` (its port stays unpublished), and the dashboard gets a "Load test" row.
- T31 results (laptop, finished Nov 4, 2026):
  - ~20 msg/s is comfortable with 1,000 users connected (end-to-end p95 80 ms). The limit is ~30 msg/s (p95 969 ms). At 40+/s it freezes.
  - The freeze was a deadlock between threads and connections, not CPU (backends ≤0.9 core, Postgres ≤0.4, of 8): a request held a connection while it waited for a thread, and the threads waited for a connection (15 connections, 40 threads). T31 first called it a leak, and tests disproved that (D34).
  - Logins: fine up to ~8/s on a fresh Docker, and they collapse at 10/s (argon2 memory). With less free memory, they tipped at 6/s.
  - The D23 subscribe lock is a real queue in a storm (wait p95 1.5-2.2 s). Gradual connects are fast (p50 6 ms).
  - The first request after a quiet minute isn't slow (T30's 0.9 s didn't come back).
  - Fixed in D34.
- Changes from the brief (accepted):
  - Fake users start at 10/s (50/s froze both copies).
  - d's steps are 10-50 msg/s, and e runs at ~10 msg/s.
  - A `live_subscribe_lock_wait_seconds` timer was added.
  - Sends happen at random moments (Poisson).
  - Claude Code took the screenshots (a read-only Grafana and headless Chrome).
  - `run.sh` waits 12 s after switching backends (D28's 10 s name re-check).

### D34. Parley under load (fixes from T31)
- What froze a copy was a deadlock: a request held a database connection while it waited for a thread, and the threads waited for a connection. It wasn't a leak: hanging up and cancelling both give the connection back (tests prove it).
- A database session opens inside the work (`with SessionLocal() as db:`, in one thread) and closes before anything waits. There's no `get_db`. `get_current_user` has its own short session.
- A send commits, reads what it needs and closes before publishing to Redis and RabbitMQ (D9's "save first" still holds). Receipts and the chat list's Redis read do the same.
- One number per copy for threads, connections and requests at work: 8 (`CAPACITY`, chosen by comparing 5, 8 and 15). `pool_size` 8, `max_overflow` 0, `pool_timeout` 2 s. Postgres has ~17 of 100 connections in use.
- Fail fast: a request waits at most 3 s for a slot, then gets 503 "Busy, try again" with `Retry-After` (1-3 s at random). A pool timeout gives the same 503. Health, metrics and the live line have no gate. `/api/health` stays a `def` route, so a copy with stuck threads fails T32's liveness probe.
- Password checks: at most 3 at once per copy, waiting up to 2 s, then the same 503. That covers sign-up and log-in.
- The app treats a 503 with `Retry-After` on a send like a 429: same `client_msg_id`, in order. A 503 without `Retry-After` keeps its old meaning. Log-in, sign-up and start-chat show "Busy, try again in a moment."
- `idle_in_transaction_session_timeout` is 60 s, set on each app connection, so a deploy doesn't restart Postgres.
- Results (laptop, Nov 6, 2026): no freeze in any run, 0 undelivered, and the limit is ~35 msg/s (it was ~30). It's now set by CPU (about one core per copy). 10 logins/s stays at ~206 MB (it was 945 MB and swapping). Other apps were open during these runs (Windows paging), so they were harder than T31's.
- Known and accepted:
  - Past the limit, accepted messages fall (37/s at 40 offered, 21/s at 60), because refusing costs CPU too.
  - A live `read` or `delivered` that hits a busy database is dropped, not the line. The app's next one carries the highest number, so the tick catches up then.
  - A page reload during overload can show the log-in screen if its refresh gets a 503 (a small fix in PLAN's Later list).
  - D23's subscribe lock is still a queue in a storm (open → hello p50 2.6 s), but nothing freezes.
- Auto-restart of a stuck copy comes with T32's liveness probe. Async SQLAlchemy (D15) isn't needed.
- Live since Nov 6, 2026 (PR #37). The deploy was green on both copies, and the live 429 check passed (401 five times, then 429). Overload behaviour isn't tested on the live site (D33); the laptop runs are the proof.

### D35. Kubernetes on the laptop (T32)
- kind (Kubernetes in Docker), one node, pinned by D27's version rule. It runs the same way on the laptop's Docker Desktop and in CI. It's free and uses nothing on AWS.
- Plain manifests with Kustomize (built into `kubectl`), in `deploy/k8s/`, namespace `parley`. No Helm. T33 can add an EKS overlay.
- The same images as Compose (D27), tagged with the commit and loaded into kind, with no registry.
- Deployments for the stateless parts: `backend` (2 replicas, D28), `worker` (1) and `web` (1). StatefulSets with one replica and a volume each for PostgreSQL, Redis and RabbitMQ. On a real cloud, these would usually be managed services.
- `migrate` is a Job that finishes before the backends start or roll, so two copies never migrate at once (D27).
- No ingress controller: Parley's own `web` Nginx stays the front door, as in Compose and production, on `localhost:8090` through kind's port mapping.
- Settings in a ConfigMap. Secrets in a Kubernetes Secret made from the local `.env` by a script, never committed (D15).
- Probes: liveness never depends on a helper, so a Redis outage never restarts the backends (D24). Heavy checks run every 30 s (D27).
- Production stays on Docker Compose on EC2 (D30, D31). Kubernetes is for learning and the demo, and T33 is the optional cloud run.
- Agreed and learned in T32 (finished Nov 7, 2026):
  - kind v0.33.0 with Kubernetes 1.36.4, pinned by digest. Leader election is off: one node doesn't need it, and on the memory-starved laptop it kept restarting the cluster's managers.
  - The backend uses a headless Service with Nginx's `upstream ... resolve` and `least_conn`. That split 13/12 every round, while a normal Service gave up to 17/8. The helpers use normal Services, so a missing pod fails in about 1 s, not after a 2 s name lookup.
  - Liveness is patient: about 60 s, and 2 minutes for PostgreSQL. At 30 s, Windows memory stalls restarted healthy pods. Readiness moves traffic away in about 15 s. The backend uses `/api/health` for both, which touches no helper (D24, D34).
  - Rolling: `maxSurge` 1, `maxUnavailable` 0, `minReadySeconds` 10. A pause before a pod stops: 6 s for the backend (Nginx re-checks names every 5 s in the cluster) and 3 s for web. Measured: 0 of 839 requests failed.
  - A name that won't resolve counts as "can't reach RabbitMQ" in `queues.connect()`. Before this, the worker crashed while RabbitMQ restarted. It's a real fix for every setup, with a test.
  - The `k8s` CI job isn't required and uses `continue-on-error`, so it can't block a deploy (`deploy.yml` waits for the whole CI run). Claude Code's after-merge check reports whether it passed.
  - `.claude/settings.local.json` is gitignored.
  - Results: all 7 demos passed. A deleted pod's lines moved within 8.8 s, a frozen pod restarted by itself in 69-74 s, and a rolling update lost 0 messages. Details are in `docs/kubernetes.md`.
- Known and accepted:
  - The laptop is the real limit (200-550 MB free with other apps open), and image loads stall everything for tens of seconds. `up.sh` takes about 9 minutes from nothing.
  - During a Redis outage, sends take 1-2 s each, because each Redis call waits out its 1 s limit (D24).
  - The worker's probes check its metrics thread. They catch a stuck pod, but not a stuck job loop inside a live process.
  - Lines don't move back after a pod is replaced. Only new lines go to the new pod.
  - A user with 5 tabs can hit the 10 tickets a minute limit (D24) while every tab reconnects. The app waits and retries.
  - RabbitMQ's memory alarm uses the machine's memory, not its 512 Mi limit. T33 should set it if RabbitMQ runs there.

### D36. README (T34)
- `README.md` is the front page, with the brief's 12 parts. Its numbers come only from `docs/load-test.md`, `docs/kubernetes.md`, DECISIONS.md and LEARNING.md. The diagrams are Mermaid, and it links to the long docs instead of copying them. Claude is mentioned only in "How I built this" (D13).
- Screenshots and the demo GIF come from the local stack, on a throwaway database with made-up people (@example.com) that's deleted afterwards.
- D-entries are headings (`### Dn. Title`), so the README can link to each one.
- Clean re-runs (Nov 7, 2026): b 11,506 saved and 11,506 received, with 3 line drops. d reached the same 37.4/s peak with 0 undelivered. The README uses b from Nov 7 and d from Nov 6 (its lines split exactly 500/500), and both docs say why.
- Learned: Nginx's `least_conn` counts open WebSockets, so a small uneven split of live lines (513/487) sent nearly all HTTP to the other copy until it was busy (a fix idea is in PLAN's Later list).

### D37. Groups (T35)
- A group is a chat with `kind = group`, a name (1-50 characters) and no `direct_key`. Direct chats don't change.
- Up to 50 members, including the creator. That keeps the fan-out small for one-core copies (D34).
- Roles are `admin` and `member`. The creator is an admin. Admins add and remove people, rename the group and make others admin. Anyone can leave. If the last admin leaves, the longest-standing member becomes admin.
- People are added from your direct chats, or by exact email (like start-chat). There's no user search or directory.
- Membership has a start and an end. A new member sees messages from when they joined, not the earlier history. A member who leaves or is removed keeps what they already had, gets nothing new and can't send. The chat stays in their list, read-only.
- Group events (created, added, removed, left, renamed, made admin) are messages too, with `kind = system` and their own number in the chat. They're saved, pushed and caught up like any message (D9, D18, D21). They hold structured data (who did what to whom), and the app writes the words.
- Fan-out: a message is published on `user:<id>` for each current member (D23), with no new channel type.
- Ticks: two grey ticks once every other current member has it delivered, and teal once every other current member has read it (the lowest bookmark, D9). Who read what ("message info") comes later.
- Receipts in groups (changed during T35, after measuring): a member's own bookmark move goes only to their own tabs. When the group's lowest `delivered` or `read` bookmark (over current members) moves, one group receipt with both lowest numbers goes to all current members, and the app draws the ticks from it. That's all the ticks show, and it means ~100 pushes per message instead of ~2,450 in a 50-member group. Direct chats keep D20's receipts. Every member change (remove, leave, or any other) also pushes the group's lowest bookmarks, since someone leaving can lift them without anyone reading. Tests cover remove and leave, both when the others have read and when they haven't. Ticks count the people in the group now, not who was there when the message was sent: it's simpler, and it fits the lowest-bookmark receipt.
- Typing goes to current members and shows the name ("Ana is typing...").
- The header shows member names, not online or last seen. Online stays for direct chats (D22).
- Notifications: one job per member (D25), titled "<sender> in <group>", with `chat_id` only (D12, D26).
- Creating groups and changing members get D24-style limits. Every group route checks membership and role on the server.
- Table changes follow expand-then-contract (D31).
- The "..." menu comes back with "New group", and a group's members show in the side panel (D8).
- Agreed and learned in T35 (Nov 8, 2026):
  - Membership is stored as message numbers: `from_seq` (the "added" note) to `until_seq` (the "left" or "removed" note). History, catch-up and pushes reuse D21's "after #N" rule.
  - Every group change locks the group's chat row, checks the person's role under that lock, and saves the change with its system note in one transaction. A send checks "still a member" under the same lock.
  - A new member's bookmarks start just before the "added" note, so they never hold back older ticks. Ticks count only current members.
  - Online status goes only to direct-chat partners. This narrows D22, since groups don't show online.
  - People are added from your direct chats (by user id) or by exact email. Each email lookup counts against start-chat's limit. New limits: 10 new groups an hour, and 30 member changes a minute, per user.
  - Group notes don't notify. "Added you" arrives live and counts as unread until T37's rule (D39). Every message carries `sender_name`, so names still show for people who have left.
  - Nov 8: by mistake, Claude Code created 3 demo accounts (ana.demo, ben.demo and cara.demo @example.com) and a group on the live site. They're harmless and stay until the server is destroyed. CLAUDE.md now forbids creating data on the live site.
  - Re-adding someone starts their view at the new "added" note. Their earlier stretch isn't shown again. Ex-members get 403 on the members list.
  - Measured before the receipt change: a 50-member group handled 5 msg/s easily without reads (p95 84 ms). With reads, receipts capped it below 2 msg/s (~2,400 pushes a second, 1.1 cores per copy). Nothing was lost from the database and no copy froze. The re-run after the change is in `docs/load-test.md` ("Groups").

### D38. Files and voice notes (T36)
- MinIO's free edition is out: it stopped publishing Docker images in Oct 2025 and its repository is archived. The store is Garage or SeaweedFS, chosen in T36 by measured memory and the S3 features needed. This replaces D29's MinIO line, and D29's rule stands: plain S3 in the code, AWS S3 only by settings.
- The store runs in Compose everywhere, including the live server (a volume on its disk, a memory limit, no AWS change and no extra cost), and in the kind setup.
- Uploads and downloads go straight between the browser and storage with short-lived presigned URLs, handed out only after a membership check (D37). Storage is reached through Nginx on the same site, so there's no cross-site setup.
- A message is saved only after its upload finishes (D9). It holds the file's key, name, type and size, and for images the size and a small preview made by the browser. The server never opens files.
- 10 MB per file. Images (JPEG, PNG, WebP, GIF), documents (PDF, TXT, DOCX, XLSX, PPTX, ZIP) and voice notes (up to 2 minutes). Uploads get D24-style limits. Uploaded but unsent files are removed after a day.
- Known gap: no backups for files, the same as the database (D30).
- Decided during T36 (Nov 8): the store is Garage. Its 4 secrets live in Parameter Store under `/parley/prod/`, like the others (D31). Adithya adds them once from his laptop with one command that shows no values. They aren't derived from `JWT_SECRET`, so a leak or rotation of one never touches the other.
- Agreed and learned in T36 (Nov 8, 2026):
  - Garage v2.4.1, chosen by measured memory: a 77 MB peak against SeaweedFS's 685 MB, in the same test (5 MB × 60, up and down, 4 at once). Metadata in sqlite, compression off, one node, a 256 MB memory limit and a 5 GB bucket limit, so uploads can't fill the disk the database lives on.
  - The four secrets are `STORAGE_RPC_SECRET`, `STORAGE_ADMIN_TOKEN`, `STORAGE_ACCESS_KEY` and `STORAGE_SECRET_KEY`. A deploy stops before changing anything if one is missing, and servers refuse Compose's laptop keys.
  - A small S3 client with no AWS SDK (D29), checked against AWS's published signature example. The signature covers the store's own Host, which Nginx sends, so the browser only sees `/storage/` on our site.
  - Presigned links last 5 minutes. Uploads sign the size and type, so the store itself refuses anything else, and the server checks them again before saving the message (D9).
  - A message stores the file's id, not a key. The key is always `chats/<chat>/<file>`, so user input never touches a path.
  - Download links go only to current members, from the message they joined at (D37). Ex-members keep the previews and the file list, but get 403 on new links.
  - Documents always download and never open on our site. HTML and SVG aren't allowed. Nginx adds `nosniff` and a sandbox header.
  - Limits: 60 uploads an hour and 300 download links a minute, per user.
  - Files have their own queue per chat, so a big upload doesn't hold up a text. A later text can get a lower number than a photo still uploading (an exception to D21's strict order, for files only).
  - The backends don't wait for the store. Chat works without it, and file routes answer 503.
  - Unsent files are removed after a day by an hourly job in the worker.
  - Results: 218 tests (38 new), 11 guards broken on purpose and each caught, and 46/46 real-browser checks.
  - Known gap: for up to 5 minutes, the sender's upload link can replace their own file with another of the same size and type (a fix is in PLAN's Later list).
  - Live since Nov 9, 2026 (PR #42). CI (including k8s) and the deploy were green. Idle on the live server: the store used 5.3 MB of its 256 MB, and the server had 1009 MB available. Even at the store's full limit, about 750 MB stays free. Unsigned `/storage/` requests get 403.

### D39. Reactions, edit and delete (T37)
- Every change to a message is an event with its own number in the chat (`reaction`, `edit`, `delete`), so catch-up by number brings it (D21). History pages return messages with the latest state applied.
- Reactions: one per person per message, from 👍 ❤️ 😂 😮 😢 🙏. Tap again to remove.
- Edit: your own text messages, within 15 minutes, marked "edited".
- Delete for everyone: your own messages, within 1 hour. The server erases the text and the file. "Delete for me" comes later.
- Unread and notifications count only real messages (text, files, voice). Events and group notes (D37) don't. This replaces D20's "newest number − read_up_to" rule.
- Agreed and learned in T37 (Nov 9, 2026):
  - Event rows hold only `target_seq`, never text. The text lives only on the message, so delete really erases it. `state_seq` is the number of the last change, and the app keeps the higher copy, since pushes can arrive out of order.
  - Each action locks the chat, checks the rules, changes the message and saves the event in one transaction. Repeating an action changes nothing and takes no number. Actions share the send limit (20 per 10 s).
  - History pages return the latest state with no events, and say which numbers they cover (`low_seq`, `high_seq`), so the app tracks covered stretches instead of hunting for holes. Catch-up returns the events, each with the current target. Pushes use `message.new`.
  - Events move no bookmarks and notify nobody. A notification job for a message deleted during its 5 s wait is skipped. A later joiner gets the event with `target: null` (D37).
  - Delete blanks the text and file details, removes the reactions and removes the file from storage. If storage is down, the upload row stays `erase_pending`, and the hourly cleanup finishes the job.
  - Routes: `PUT` and `DELETE /{seq}/reaction`, `PATCH /{seq}` and `DELETE /{seq}`. Desktop uses hover and touch uses a long press, with "Copy" in the phone menu.
  - Results: 257 tests (39 new), with each deliberate bug caught, and 14 real-browser checks.
  - Known and accepted: event rows are never compacted. A tab left open across this deploy shows blank bubbles for events until it reloads. An unread badge moved from another tab can stay a little high until the next 60 s re-check.
  - Live since Nov 9, 2026 (PR #43, a31cdf9), with CI and the deploy green.

### D40. Search (T38)
- Search runs only in the browser (D12). The server has no text search.
- The app keeps the messages it has seen in IndexedDB, per user, and clears them on log-out. Edits and deletes update the copy.
- It searches what this device has loaded, and says so. An optional button loads older history.
- Agreed and learned in T38 (Nov 9, 2026):
  - The chat list carries `last_seq` (the last number I can see, events included, stopping where a member left). Each chat on the device has a mark meaning "changes up to here are applied here". Live pushes move the mark only when they're the next number. The list's re-check fetches `after=<mark>` only when `last_seq` is ahead, so edits and deletes made while the device was away still reach the copy. Usually that means no extra requests at all.
  - A deleted message stays as an empty row with no text, and the higher `state_seq` wins, so a late copy can't bring it back.
  - Log-out deletes the device's database, and other tabs stop writing to it. A session that really ended (401 on refresh) erases it too, and a different user's login removes any leftover.
  - Text and file names are searchable. Voice notes and group notes aren't. Results are capped at the newest 100, and the app says so.
  - "Load all my history" fetches one page of 100 at a time with a 250 ms pause. It can be stopped, and it resumes where it stopped.
  - Results: 261 tests (4 new), and 54 of 54 real-browser checks at three window sizes. No request carried the searched words.
  - Known and accepted: the copy has no size limit and isn't encrypted on the device. A search reads every row, about 0.5 s at 20,000.