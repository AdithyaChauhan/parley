# Parley: Project Plan

Parley is a real-time chat web app, like WhatsApp Web. It's a portfolio project to learn and show backend system design.

**How to use this file**
- One task at a time. Each task = one branch = one pull request.
- "You are here" shows the current task and its brief.
- After a pull request merges, Adithya tells the planning chat. The planner sends back a new PLAN.md (box ticked, "You are here" moved to the next task). Adithya replaces the file, and that goes in the next task's branch.
- Only the planner (chat Claude) writes task briefs. Claude Code never edits this file. It can only suggest changes.
- Adithya may write a file himself if he wants. He tells Claude Code, so it knows.
- npm audit's "braces" warnings: dev-only and no fixed version yet. Don't raise them again until a fix exists.
- Never commit straight to `main`. Even a small fix goes through a branch and a PR (D13).
- Before merging, paste the PR description. Proof steps (like a red-cross test) use a throwaway PR that's closed without merging, and the run links go in the report.
- Each task's "Done when" also needs the task's "In my words" in LEARNING.md filled in by Adithya. For frontend tasks (fast mode, see CLAUDE.md), Claude Code drafts it and Adithya just reviews it.

---

## You are here

### Task 14: Start a chat, send a message, load history 30 at a time (teaching mode)
- **Branch:** `feature/messages-api`
- **Goal:** the first real chat routes. Two logged-in people can start a direct chat, send messages (numbered safely by T13's `add_message`), and load older messages page by page. Tested in `/docs` and by pytest. Screens connect in T15.
- **Mode:** teaching mode. New style (CLAUDE.md updated): show a small example table first, then explain, then ask a "how does X work" question.

**Carry-over (do first):** restore the full Task 13 section in LEARNING.md (heading, "What was built", "New ideas") around Adithya's own "In my words" text, which stays exactly as he wrote it.

**Example first: how paging works (Claude Code shows this before writing code).** A chat has messages #1 to #70.
```
 Request                                 Gets               has_more
 GET /messages                     →     #70 ... #41        true
 GET /messages?before=41           →     #40 ... #11        true
 GET /messages?before=11           →     #10 ... #1         false
```
Newest first, 30 at a time, using the message numbers (never page numbers or times), so a new message arriving never shifts a page.

**Routes (all need the access token; all under `/api`):**
1. `POST /api/chats/direct` with `{ "email": "..." }`: start a direct chat with that person, or return the one that already exists.
   - Your own email gives 400, and an unknown email gives 404.
   - Uses a `direct_key` helper (the two user ids sorted, joined with ":") and adds both people to `chat_members`.
   - If two "start chat" requests collide on the unique `direct_key`, catch the refusal and return the existing chat (same pattern as `add_message`).
   - Replies 201 when new, 200 when it already existed.
2. `GET /api/chats`: my chats, newest activity first. Each has:
   - `id` and `kind`;
   - a display name (the other person's name for direct chats);
   - the last message (number, start of the text, time);
   - `unread` = `last_seq - read_up_to`.
3. `POST /api/chats/{chat_id}/messages` with `{ "client_msg_id": "<uuid>", "body": "..." }`:
   - Not a member of the chat (or no such chat) gives 404, which doesn't reveal that the chat exists.
   - The body is trimmed, 1 to 4000 characters.
   - It calls `add_message`. A new message gives 201; a repeat of the same `client_msg_id` gives 200 with the first copy.
4. `GET /api/chats/{chat_id}/messages?before=N&limit=30`: newest first.
   - `limit` is at most 100.
   - The reply is `{ "messages": [...], "has_more": true/false }`.
   - Not a member gives 404.

**Agreed fixes:** `add_message` returns `(message, created)` so the route can pick 201 or 200; sending #N also sets the sender's own `read_up_to` to N (your own messages are never unread); add `app/messages/schemas.py`.

**Code layout (D5):** `app/chats/schemas.py`, `service.py` (`direct_key`, get-or-create direct chat, list my chats), `routes.py`; `app/messages/routes.py` (send and history), using `add_message`. Plug both routers into the `/api` router.

**Tests (always the `client` fixture):** a test for each rule above. Also a two-user story: A starts a chat with B, A sends 3, B sees them in order, B's `unread` is 3, and C (not a member) gets 404.

- **Not in this task:** read and delivered ticks (T17/T18), groups (v2), live updates (T16+), screens (T15).
- **Done when:** the two-user story works in `/docs` with two accounts, all tests pass locally and in CI (paste the green run link in the report), and Adithya has filled in "In my words".

Questions for Adithya ("how does X work"): how paging with `before` works; how the server stops a non-member reading a chat; how a repeated send is turned into the first copy.

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
- [ ] T14. Send a message and load history, 30 at a time
- [ ] T15. Connect the chat list and conversation screens to real data (check: leave the app open 15+ minutes, then load chats without reloading, to test the 401 → refresh → retry path) (check: leave the app open 15+ minutes, then load chats without reloading, to test the 401 → refresh → retry path)

### Phase 4: Live chat (WebSocket)
- [ ] T16. WebSocket connection with a one-time ticket (explain the ticket idea on its own first)
- [ ] T17. New messages appear instantly; "got it" replies give two ticks
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
- [ ] T31. README with an architecture diagram, screenshots, a demo video and the load-test results

### Later
- End-to-end encryption phase: 1:1 text, one device, safety numbers (see D12) (chat-list previews then move to the app, since the server can't read the text)
- v2: groups, images and voice notes, reactions, edit and delete, search
- Optional: move notifications into their own service