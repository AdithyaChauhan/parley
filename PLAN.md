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

### Task 21: Two backend copies, live messages cross between them (Redis pub/sub) (teaching mode, friend style)
- **Branch:** `feature/two-copies`
- **Goal:**
  - Run **two copies** of the backend at once. Ana talks to copy A, Ben to copy B, and chat, ticks, typing and online status still work instantly.
  - Tickets move into Redis, so a ticket made by one copy works on the other.
  - This is the system design highlight of Parley.
- **Mode:** teaching mode, friend style, questions at the end as "In my words" prompts. Claude Code runs the checks itself and shows the results.

**Example first (Claude Code shows this before any code):**
```
 Today (one copy): Ana sends → copy A saves #30 → copy A's switchboard → Ben's line. Works.

 Two copies, no pub/sub:
   Ana ── copy A        Ben ── copy B
   Ana sends → copy A saves #30 → copy A's switchboard: "Ben? Not on my lines." → Ben sees nothing. ✗

 Two copies WITH Redis pub/sub (a radio: shout on a channel, whoever listens hears it):
   copy A: "Ben is on my lines"  → listens on channel user:<Ben>   (only while Ben has a line here)
   copy B: "Ana is on my lines"  → listens on channel user:<Ana>
   Ana sends → copy A saves #30 (PostgreSQL first, D9)
             → copy A shouts message.new on user:<Ben> and user:<Ana>
             → copy B hears user:<Ben> → Ben's line ✓      copy A hears user:<Ana> → Ana's other tabs ✓
```
Pub/sub doesn't remember anything. If no copy is listening, the shout is lost. That's fine, because the message is already saved and T19's catch-up fetches anything missed (D20, D21).

**Steps:**
1. **Tickets in Redis:**
   - `issue` stores `ticket:<t>` with the user id and a 30 s Redis timer.
   - `redeem` uses `GETDEL`, which reads and deletes in one go, so a ticket still works only once, even if two copies try it at the same moment.
2. **Which copy am I:** a `COPY_NAME` setting (default "A"), shown in `GET /api/health`, so you can check which copy a window talks to.
3. **`app/live/bus.py`, the radio:**
   - `publish(user_ids, event)` shouts the event on `user:<id>` for each person. There's a normal version for normal routes (no more `anyio.from_thread` hand-off) and an async one for the live line.
   - `listen()` runs in the background for the copy's whole life (started in `main.py`'s lifespan). It hands each event it hears to the local switchboard. If Redis drops, it waits a moment and starts listening again.
4. **Switchboard:**
   - On a user's first line on this copy, subscribe to `user:<id>`. When their last line here closes, unsubscribe.
   - Every push now goes through `bus.publish`, never straight to the switchboard: `message.new`, `receipt`, `typing` and `presence`.
5. **Running two copies locally:**
   - Copy A: `uvicorn app.main:app --port 8000` with `COPY_NAME=A`. Copy B: `--port 8001` with `COPY_NAME=B`.
   - The Vite proxy target comes from a setting (default 8000). A second Vite runs on port 5174 pointing at 8001.
   - Ana uses http://localhost:5173 (copy A). Ben uses http://localhost:5174 in Incognito (copy B).
6. **Tests:**
   - A ticket from Redis works once, a second redeem gets nothing, and the 30 s timer is set.
   - A push still reaches the other person's line after going through Redis and back.
   - Unsubscribe happens when the last line closes.
   - The listener keeps going after a bad event.
   - All 63 existing tests still pass.
- **Not in this task:** automatic switch-over when a copy dies (that needs Nginx in front, T26), spam limits (T22).
- **Done when:**
  - Ana on 5173 (copy A) and Ben on 5174 (copy B): `/api/health` shows A and B. Messages, ✓ → ✓✓ → teal, typing and online status all work instantly between them.
  - Stop copy A: Ana's dot goes grey, and Ben keeps working. Start copy A again: Ana reconnects and catches up, with nothing lost and no doubles.
  - All tests pass, CI is green (run link in the report), and "In my words" is filled in by Adithya.

"In my words" prompts: why two copies broke live chat before pub/sub; how a message from copy A reaches Ben's line on copy B; why losing a pub/sub shout is OK in Parley.

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
- [ ] T21. Two backend copies; live messages cross between them (pub/sub)
- [ ] T22. Spam limits (also decide what happens when Redis is down: today the live line and chat list fail, like when PostgreSQL is down)

### Phase 6: RabbitMQ
- [ ] T23. Notification worker with retries and a failed-jobs queue
- [ ] T24. Browser push notifications (Web Push). Push text must not contain message text (see D12). Web Push needs HTTPS (localhost counts); check again at T26

### Phase 7: Run it like production
- [ ] T25. Dockerfiles and Docker Compose for every part
- [ ] T26. Nginx in front of several backend copies (demo: stop one copy mid-chat and the apps reconnect to the other through Nginx, with nothing lost) (turn on `secure=True` for the refresh cookie once HTTPS is on)

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