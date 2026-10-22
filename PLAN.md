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

### Task 16: The live connection (WebSocket) with a one-time ticket (teaching mode, friend style)
- **Branch:** `feature/live-connection`
- **Goal:** each open tab keeps one "phone line" open to the server, so in T17 the server can push new messages instantly. This task only opens the line safely and proves it works. Nothing is pushed yet except a hello.
- **Mode:** teaching mode, friend style (CLAUDE.md). Example first, then short explanation, then a "how does X work" question.

**Example first (Claude Code shows this before any code):**
```
 Today (HTTP):      Ben's app asks "anything new?"  → server answers → line closes
                    Ben only sees Ana's message when he reloads.
 With a WebSocket:  Ben's app opens a line once and keeps it open.
                    Server can say "new message!" any time, like a phone call vs. sending letters.

 Getting on the line (the ticket):
 1. Ben's app → POST /api/live/ticket   (shows its access token, like any request)
 2. Server   → { "ticket": "x7Kq...", "expires_in": 30 }   one use only, 30 seconds
 3. Ben's app → opens  ws://.../api/live?ticket=x7Kq...
 4. Server checks the ticket, crosses it off (can't be used again), and says:
               { "type": "hello", "data": { "user_id": "..." } }
```
Why a ticket: a browser can't add the "Authorization" header to a WebSocket, and putting the real 15-minute token in the address would leave it in logs. A ticket that dies after one use or 30 seconds is safe to put there.

**Steps:**
1. **Package:** add `websockets` (lets uvicorn speak WebSocket; named in D19). Pin the exact version.
2. **`app/live/tickets.py`:** a small in-memory ticket store (D19).
   - `issue(user_id)` makes a random ticket that lasts 30 seconds.
   - `redeem(ticket)` returns the user id once, then the ticket is gone. Expired or unknown gives nothing.
   - Lock it with a thread lock, since requests can arrive at the same time.
3. **`app/live/manager.py`:** the switchboard. It remembers which open lines belong to which user (one user can have several tabs), with `connect`, `disconnect` and `send_to_user(user_id, event)`. `send_to_user` is used in T17.
4. **`app/live/routes.py`:**
   - `POST /api/live/ticket` needs the access token and returns `{ticket, expires_in}`.
   - The WebSocket `/api/live?ticket=...`:
     - A bad, used or expired ticket closes with code 4401.
     - A good ticket accepts the line, registers it, and sends `hello`.
     - When the tab closes, the line is removed from the switchboard.
5. **Vite proxy:** allow WebSocket on `/api` (`ws: true`).
6. **Frontend `src/lib/live.ts` (fast mode, small):**
   - After log-in, get a ticket and open the line.
   - Show a small dot on your avatar: green when connected, grey when not.
   - Close the line on log-out.
   - No auto-reconnect yet (T19).
7. **Tests:**
   - The ticket route needs the token.
   - A ticket works once; the second use is refused.
   - An expired ticket is refused (fake the clock).
   - A good ticket gets `hello` with the right user id.
   - Two tabs of the same user are both in the switchboard; after one closes, one is left.
- **Not in this task:**
  - Pushing real messages (T17). Note for T17: the send route runs in a worker thread, so pushing from it to the live line needs a safe hand-off to the async side.
  - Ticks and typing (T17/T18), reconnecting (T19), Redis (T20/T21).
- **Done when:**
  - The dot turns green after log-in and grey after you stop the backend.
  - In the browser DevTools Network tab (filter "WS"), you can see the hello message.
  - All tests pass locally and in CI (run link in the report), and Adithya has filled in "In my words".

Questions for Adithya ("how does X work"): how the ticket gets you onto the line without the real token in the address; how the server knows which open line is Ben's; what happens to the switchboard when Ben has two tabs and closes one.

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
- [ ] T16. WebSocket connection with a one-time ticket (explain the ticket idea on its own first)
- [ ] T17. New messages appear instantly; "got it" replies give two ticks (also keep a "Not sent" message in the chat when you switch chats and come back)
- [ ] T18. Typing indicator and read ticks
- [ ] T19. Reconnect and catch up on missed messages

### Phase 5: Redis
- [ ] T20. Online and last seen, with automatic expiry
- [ ] T21. Two backend copies; live messages cross between them (pub/sub)
- [ ] T22. Spam limits

### Phase 6: RabbitMQ
- [ ] T23. Notification worker with retries and a failed-jobs queue
- [ ] T24. Browser push notifications (Web Push). Push text must not contain message text (see D12). Web Push needs HTTPS (localhost counts); check again at T26

### Phase 7: Run it like production
- [ ] T25. Dockerfiles and Docker Compose for every part
- [ ] T26. Nginx in front of several backend copies (turn on `secure=True` for the refresh cookie once HTTPS is on)

### Phase 8: Measure it
- [ ] T27. Prometheus metrics and a Grafana dashboard
- [ ] T28. Load test with 1,000 fake users; write up the results with the laptop's specs

### Phase 9: Kubernetes
- [ ] T29. Run Parley on local Kubernetes
- [ ] T30. Optional, only if ready before the AWS free plan ends (around mid-December 2026): short EKS run with Terraform, and record a demo

### Phase 10: Show it
- [ ] T31. README with an architecture diagram, screenshots, a demo video and the load-test results, plus a short "How I built this" section (planned with Claude, coded with Claude Code; Adithya made the decisions, reviewed and tested every change; LEARNING.md shows what he learned)

### Later
- End-to-end encryption phase: 1:1 text, one device, safety numbers (see D12) (chat-list previews then move to the app, since the server can't read the text)
- v2: groups, images and voice notes, reactions, edit and delete, search
- Optional: move notifications into their own service