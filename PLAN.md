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

### Task 24: Real browser notifications (Web Push) (teaching mode for the backend, fast mode for the app)
- **Branch:** `feature/web-push`
- **Goal:** T23's worker stops writing a log line and sends a real notification to Ben's browser: "New message from Ana", with no message text (D12). It works even when Ben's Parley tab is closed, as long as his browser is running.
- **Mode:** backend in teaching mode (example first, short, "In my words" questions at the end). The app part (permission button, service worker) is fast mode. Every few steps, give a short "done / next / what I need from you" recap.

**Example first (Claude Code shows this before any code):**
```
 Once, on Ben's browser:
   Ben clicks "Turn on notifications" → browser asks → Allow
   browser → push service (Google's for Chrome/Edge, Mozilla's for Firefox) → gives an address + 2 keys
   app → POST /api/push/subscribe {endpoint, keys} → saved in push_subscriptions (Ben, device 1)

 Every missed message:
   worker (T23) → "Ben, #42 unread after 5 s" → for each of Ben's devices:
     encrypt {"title":"New message from Ana","chat_id":..} with that device's keys, sign with our VAPID key
     POST to the device's push address
       201 → sent, note it for that device
       404/410 → this device unsubscribed → delete the row, don't retry
       429/5xx/timeout → retry later (T23 retries)
   push service → Ben's browser wakes the service worker (sw.js) → shows the notification
```
- **VAPID** is a key pair that proves the push came from Parley. The public key goes to the browser, and the private key stays in `.env`.
- The **service worker** is a small script the browser keeps alive even when the tab is closed.
- The **push service** only passes the box along. It can't read it, because it's encrypted for Ben's browser.

**Steps:**
1. **Setup:**
   - Add `pywebpush`, pinned to the latest stable on PyPI (check, don't guess).
   - Make the VAPID keys once with a one-line command Claude Code gives. Adithya puts `VAPID_PRIVATE_KEY`, `VAPID_PUBLIC_KEY` and `VAPID_SUBJECT` (a `mailto:` address) in `.env`, never in a chat or a commit. `.env.example` gets placeholders.
   - Also fix `.env.example`'s `REDIS_URL` and `TEST_REDIS_URL` to use `127.0.0.1` (D22).
2. **Table `push_subscriptions`** (Alembic migration, and add it to the conftest TRUNCATE):
   - Columns: `id` (UUID), `user_id`, `endpoint` (unique), `p256dh`, `auth`, `created_at`.
   - One row per browser per user.
3. **Routes:**
   - `GET /api/push/key` returns the public key.
   - `POST /api/push/subscribe` saves the device. If that endpoint already exists, it moves to the current user, since another person may have logged in on the same browser.
   - `DELETE /api/push/subscribe` with `{endpoint}` deletes only the current user's own row.
   - Limit: 10 subscribes per minute per user (D24 style).
4. **`WebPushNotifier`**, with the new shape `send(job, user_name, title)` returning the outcome (D25, D26):
   - It sends to each of the user's devices that isn't noted yet.
   - The Redis note becomes per device: `notified:<message>:<subscription>` (24 h). A retry only tries the devices that failed, so a phone that already got it isn't notified twice.
   - 404/410 deletes that row and doesn't retry. 429, 5xx or a timeout raise `NotifyFailed`, so T23 retries.
   - A user with no devices is skipped with "no devices".
   - The payload is the title and `chat_id` only, with a TTL of 1 hour (an old notification is useless).
   - `LogNotifier` stays for tests and for `NOTIFY_FAKE_FAIL_TIMES`. A setting picks which notifier the worker uses.
5. **App (fast mode):**
   - `public/sw.js`: on push, show the notification with `tag = chat_id`, so many messages from one chat replace each other instead of piling up. On click, focus an open Parley tab, or open one.
   - A small "Turn on notifications" button in the profile area. Never ask on page load, because browsers punish that.
   - If permission is already given, re-send the subscription after log-in, since it may belong to someone else now.
   - **Log out:** unsubscribe in the browser and `DELETE` the row first, so a shared computer stops getting Ben's notifications.
6. **Tests** (fake the push service, so no real network):
   - 201 marks that device as sent. 410 deletes the row and doesn't retry. 500 retries. Two devices where one is OK and one gives 500: the retry only tries the failed one.
   - Subscribe moves an existing endpoint to the new user. Unsubscribe can't delete someone else's row.
   - The payload has no message text.
   - A user with no devices is skipped.
- **Claude-run checks:** anything with multi-minute waits (retry timings) is run by Claude Code itself, with results shown. Adithya does only the browser checks.
- **Not in this task:** notification settings or mute, showing message text (only with E2EE later), and phones with the browser closed.
- **Done when:**
  - Ben uses a **second browser** (Edge or Firefox; Incognito windows usually can't get push) and clicks "Turn on notifications" → Allow.
  - Ben closes his Parley tab, but keeps the browser open. Ana sends, and about 5 s later Windows shows "New message from Ana", with no text. Clicking it opens Parley.
  - Ana sends 3 quickly, and Ben ends up with one notification for that chat, not three.
  - Ben has the chat open and reads at once: no notification.
  - Ben logs out, Ana sends, and no notification arrives.
  - If nothing shows: check Windows notification settings and Focus Assist / Do Not Disturb first.
  - All tests pass, CI is green (run link in the report), and "In my words" is filled in by Adithya.

"In my words" prompts: how Parley reaches Ben's browser when his tab is closed (push service plus service worker); why a 410 deletes the device but a 500 retries; why the "already sent" note is per device, not per person.

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
- [x] T22b. Fix: reads and ticks reach the server without the live line (HTTP door for `read` and `delivered`)

### Phase 6: RabbitMQ
- [x] T23. Notification worker with retries and a failed-jobs queue
- [ ] T24. Browser push notifications (Web Push). Push text must not contain message text (see D12). Web Push needs HTTPS (localhost counts); check again at T26

### Phase 7: Run it like production
- [ ] T25. Dockerfiles and Docker Compose for every part (the worker gets its own container; the backend and worker start only once PostgreSQL, Redis and RabbitMQ are healthy, since the backend can't start while Redis is down) (the worker needs a SIGTERM handler, since `docker stop` sends SIGTERM, not Ctrl+C)
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