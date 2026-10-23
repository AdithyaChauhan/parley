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

### Task 20: Online and "last seen", with Redis (teaching mode, friend style)
- **Branch:** `feature/presence`
- **Goal:**
  - A green dot and "online" when the other person has Parley open.
  - "last seen today at 11:15" when they don't.
  - This brings in **Redis**, the tool Phase 5 is built on (D10).
- **Mode:** teaching mode, friend style, questions at the end as "In my words" prompts. Claude Code runs the backend checks itself and shows the results.

**Example first (Claude Code shows this before any code):**

What Redis is: a whiteboard kept in memory. It's very fast, and each note can have a timer, after which it wipes itself. PostgreSQL is the filing cabinet (safe, permanent). Redis is the whiteboard (fast, temporary). "Online" is a whiteboard kind of fact.

```
 Redis key  presence:<Ben>   (a "sorted set": each open tab, with an "alive until" time)
   tab        alive until
   tab-a1     10:01:25        ← every ping (25 s) pushes this 60 s ahead
   tab-b7     10:01:10

 Ben is online  =  at least one tab whose "alive until" is still in the future.
 Ben closes tab-a1          → its row is removed. tab-b7 still alive → still online.
 Ben's laptop crashes       → no goodbye at all, but tab-b7's time passes → offline by itself.
 Redis key  last_seen:<Ben> = 10:00:25   (updated on every ping, so it's right even after a crash)
```
Why per tab, not one "online" flag: one flag breaks with two tabs (closing one would say offline) and with a crash (nobody says goodbye). The timer fixes both, and it keeps working with two backend copies in T21, because Redis is shared.

**Steps:**
1. **Redis in Docker Compose:**
   - A `redis` service using the official image, pinned to a current stable version (checked in its docs), with a health check (`redis-cli ping`).
   - `REDIS_URL` and `TEST_REDIS_URL` (`redis://localhost:6379/15`) go in `.env` and `.env.example`. Tests refuse to run unless `TEST_REDIS_URL` points at database 15, like the `_test` rule.
   - The async Redis client opens when the app starts and closes when it stops (in `main.py`), so each test's event loop gets a working client.
   - CI gets a Redis service too.
2. **Package:** `redis` (redis-py), pinned (D22). It has a normal client for normal routes and an async one for the live line.
3. **`app/presence/service.py`** (D5 folder). Each change returns whether the person just came online or just went offline.
   - `tab_alive(user_id, tab_id)`: add or refresh the tab's "alive until" (now + 60 s), keep the key's own timer at 60 s, and update `last_seen`.
   - `tab_closed(user_id, tab_id)`: remove the tab.
   - `is_online(user_id)` and `last_seen(user_id)`: clear out dead tabs first, then answer.
4. **Live line:**
   - On hello, call `tab_alive`. On every `ping`, call `tab_alive` again. When the line ends, call `tab_closed`.
   - When someone comes online or goes offline, push `presence` `{user_id, online, last_seen}` to everyone who shares a chat with them (through this copy's switchboard; T21 adds the other copies).
5. **API:** the chat list rows (and `POST /api/chats/direct`) gain `online` and `last_seen` for the other person in direct chats.
6. **App (fast mode):**
   - Green dot on the avatar in chat rows and the conversation header.
   - The header says "online", or "last seen today at 11:15" / "yesterday at 09:02" / "15.09 at 18:40", or "last seen recently" if unknown.
   - `presence` events update it live.
   - The open chat re-checks every 60 s, which catches crashed tabs that never said goodbye.
7. **Tests** (real Redis, wiped after each test):
   - One tab: online; closed: offline.
   - Two tabs, close one: still online.
   - A tab that stops pinging goes offline after its time passes (fake the clock).
   - `last_seen` is set.
   - Coming online and going offline push `presence` to a chat partner, but not to a stranger.
   - The chat list shows `online` / `last_seen`.
- **Not in this task:** two backend copies and pub/sub (T21), hiding your last seen (v2), group presence (v2).
- **Done when:**
  - Ana and Ben (normal window plus Incognito): Ben sees Ana "online". Ana closes her window: Ben sees "last seen today at ..." within a second, with no reload.
  - Ana opens two tabs and closes one: still online.
  - A tab that goes silent (in Ana's tab: DevTools → Sources → press F8 to pause it; her pings stop but the line stays open): within about 2 minutes Ben sees her offline (60 s alive + up to 60 s until Ben's check).
  - All tests pass, CI is green (run link in the report), and "In my words" is filled in by Adithya.

"In my words" prompts: what Redis is and why "online" lives there and not in PostgreSQL; how the "alive until" times handle two tabs and a crash; how Ben's screen learns that Ana went offline.

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
- [ ] T20. Online and last seen, with automatic expiry
- [ ] T21. Two backend copies; live messages cross between them (pub/sub)
- [ ] T22. Spam limits (also decide what happens when Redis is down: today the live line and chat list fail, like when PostgreSQL is down)

### Phase 6: RabbitMQ
- [ ] T23. Notification worker with retries and a failed-jobs queue
- [ ] T24. Browser push notifications (Web Push). Push text must not contain message text (see D12). Web Push needs HTTPS (localhost counts); check again at T26

### Phase 7: Run it like production
- [ ] T25. Dockerfiles and Docker Compose for every part
- [ ] T26. Nginx in front of several backend copies (turn on `secure=True` for the refresh cookie once HTTPS is on)

### Phase 8: Measure it
- [ ] T26b. Deploy Parley live on one AWS EC2 server: Docker Compose + Nginx + HTTPS (a cheap domain or a free subdomain), refresh cookie `secure=True`. First: set an AWS budget alert (about $10), and check the old delivery-delay Fargate service in ap-southeast-1 is stopped.
- [ ] T27. Prometheus metrics and a Grafana dashboard
- [ ] T28. Load test with 1,000 fake users; write up the results with the laptop's specs

### Phase 9: Kubernetes
- [ ] T29. Run Parley on local Kubernetes
- [ ] T30. Optional, only if ready before the AWS free plan ends (around mid-December 2026): short EKS run with Terraform, and record a demo. Tear it all down the same day with `terraform destroy` (the cluster costs money every hour)

### Phase 10: Show it
- [ ] T31. README with an architecture diagram, screenshots, a demo video and the load-test results, plus a short "How I built this" section (planned with Claude, coded with Claude Code; Adithya made the decisions, reviewed and tested every change; LEARNING.md shows what he learned)

### Later
- End-to-end encryption phase: 1:1 text, one device, safety numbers (see D12) (chat-list previews then move to the app, since the server can't read the text)
- v2: groups, images and voice notes, reactions, edit and delete, search
- Optional: move notifications into their own service