# Parley: Project Plan

Parley is a real-time chat web app, like WhatsApp Web. It's a portfolio project to learn and show backend system design.

**How to use this file**
- One task at a time. Each task = one branch = one pull request.
- "You are here" shows the current task and its brief.
- After a pull request merges, Adithya tells the planning chat. The planner sends back a new PLAN.md (box ticked, "You are here" moved to the next task). Adithya replaces the file, and that goes in the next task's branch.
- Only the planner (chat Claude) writes task briefs. Claude Code never edits this file. It can only suggest changes.
- Adithya may write a file himself if he wants. He tells Claude Code, so it knows.
- Never commit straight to `main`. Even a small fix goes through a branch and a PR (D13).
- Before merging, paste the PR description. Proof steps (like a red-cross test) use a throwaway PR that's closed without merging, and the run links go in the report.
- Each task's "Done when" also needs the task's "In my words" in LEARNING.md filled in by Adithya. For frontend tasks (fast mode, see CLAUDE.md), Claude Code drafts it and Adithya just reviews it.

---

## You are here

### Task 13: Chat tables and safe message numbers (teaching mode, short, Excel picture)
- **Branch:** `feature/chat-tables`
- **Goal:** the three chat sheets exist, and the database itself makes sure messages get #1, #2, #3 with no gaps or doubles, even when two people send at the same instant. Also fix the small refresh race found in T12 (same idea: a row lock).
- **Mode:** teaching mode, short explanations, Excel picture.

**The table map (Excel picture: each box is a sheet):**
```
 users ──< chat_members >── chats ──< messages
   │        (who is in        (one row     (#1, #2, #3
   │         which chat,       per chat,    per chat)
   │         + ticks)          + counter)
 sessions
 ──<  means "one row here, many rows there"
```

**The big idea: a row lock (Claude Code explains this first, ~5 lines).**
Two people send a message to the same chat at the same moment. Both read "last number = 7" and both write #8: that's a clash. A row lock is like Excel saying "someone else is editing this cell, wait". The first sender locks the chat's row, takes #8 and lets go; the second waits a few milliseconds, then takes #9.

**Steps:**
0. **Refresh race fix (from T12):** in `POST /api/auth/refresh`, load the session row with `.with_for_update()`, so two refreshes with the same cookie can't both rotate it. Add a test.
1. **`app/chats/models.py`:**
   - `chats`: `id` (UUID), `kind` ("direct" or "group"), `title` (empty for direct chats), `direct_key` (unique; for direct chats it's the two user ids sorted and joined, so the same two people can't get two direct chats), `last_seq` (whole number, starts at 0: the counter), `created_at`.
   - `chat_members`: `chat_id` + `user_id` together are the key (one row per person per chat), `joined_at`, `delivered_up_to` and `read_up_to` (whole numbers, start at 0: the two D9 bookmarks for ticks). Index on `user_id` (for "list my chats").
2. **`app/messages/models.py`:** `messages`: `id` (UUID), `chat_id`, `seq` (the number), `sender_id`, `client_msg_id` (UUID made by the sender's app, D9), `body` (text), `created_at`.
   - Unique `(chat_id, seq)`: no two #8s in one chat.
   - Unique `(sender_id, client_msg_id)`: a retried send is never saved twice.
3. **Migration:** `alembic revision --autogenerate -m "create chats, chat_members, messages"`. Read it together before `alembic upgrade head`. Check with `\dt` and `\d messages`.
4. **`app/messages/service.py`:** one function, `add_message(db, chat_id, sender_id, client_msg_id, body)`:
   - If this `(sender_id, client_msg_id)` already exists, return that message (no new row).
   - Otherwise, in one transaction: `UPDATE chats SET last_seq = last_seq + 1 WHERE id = ... RETURNING last_seq` (this locks the row), then insert the message with that number.
   - No routes yet (T14).
5. **Tests (`client` fixture or a db fixture; add the new tables to the conftest TRUNCATE):**
   - three messages get 1, 2, 3;
   - the same `client_msg_id` twice gives one row;
   - two chats count separately;
   - two threads sending at the same time get two different numbers and no error.
- **Not in this task:** send and history routes (T14), screens (T15), groups UI.
- **Done when:** tables exist (`\dt`), all tests pass locally and in CI (green tick), the concurrency test passes several runs in a row, and Adithya has filled in "In my words".

Questions for Adithya (short): what a row lock does; why `client_msg_id` stops double messages; why the counter lives on the chat row and not in Python.

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
- [ ] T13. Chat tables (start the brief with the table map; add the new tables to the conftest TRUNCATE; route tests always use the `client` fixture): chats, chat members, messages (per-chat numbers, message IDs). The brief must explain how two messages sent at the same moment never get the same number (a lock or a counter column)
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
- End-to-end encryption phase: 1:1 text, one device, safety numbers (see D12)
- v2: groups, images and voice notes, reactions, edit and delete, search
- Optional: move notifications into their own service