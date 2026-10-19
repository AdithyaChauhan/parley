# Parley: Project Plan

Parley is a real-time chat web app, like WhatsApp Web. It's a portfolio project to learn and show backend system design.

**How to use this file**
- One task at a time. Each task = one branch = one pull request.
- "You are here" shows the current task and its brief.
- After a pull request merges, Adithya tells the planning chat. The planner sends back a new PLAN.md (box ticked, "You are here" moved to the next task). Adithya replaces the file, and that goes in the next task's branch.
- Only the planner (chat Claude) writes task briefs. Claude Code never edits this file. It can only suggest changes.
- Adithya may write a file himself if he wants. He tells Claude Code, so it knows.
- Each task's "Done when" also needs the task's "In my words" in LEARNING.md filled in by Adithya. For frontend tasks (fast mode, see CLAUDE.md), Claude Code drafts it and Adithya just reviews it.

---

## You are here

### Task 9: First tables with SQLAlchemy and Alembic: users, sessions (teaching mode)
- **Branch:** `feature/db-tables`
- **Goal:** the FastAPI app connects to PostgreSQL, and the first two tables exist, created by an Alembic migration. No sign-up logic yet (that's T10).
- **Mode:** full teaching mode.
- **How the pieces fit:**
```
 .env (DATABASE_URL) ──read by──> config.py (settings)
                                      │
 models.py (User, UserSession) ──>│ db.py (engine + session) ──SQL──> PostgreSQL "db" container
                                      │
 Alembic migration ──reads models, writes CREATE TABLE──> PostgreSQL
 GET /health/db ──"select 1"──> PostgreSQL   (proves the app can reach the database)
```
- **New packages (count as part of D6):** sqlalchemy (2.x), psycopg (the PostgreSQL driver, `psycopg[binary]`), alembic, pydantic-settings (reads `.env`). Pin exact versions.
- **Steps:**
  1. Add `DATABASE_URL` to `.env.example` and your `.env` (built from the same user, password and database name, host `localhost`, port 5432).
  2. `backend/app/config.py`: one Settings class that reads `DATABASE_URL` from the root `.env`.
  3. `backend/app/db.py`: the engine, a session maker, the `Base` class for models, and a `get_db` dependency that opens and closes one session per request.
  4. `backend/app/auth/models.py` (feature folder, D5). Python class names `User` and `UserSession` (so it isn't confused with SQLAlchemy's own Session); table names stay `users` and `sessions`:
     - `users`: `id` (UUID), `email` (unique, plus a CHECK rule that it equals `lower(email)`), `name`, `password_hash`, `created_at`.
     - `sessions`: `id` (UUID), `user_id` (points to `users.id`, deleted with the user), `refresh_token_hash`, `created_at`, `expires_at`, `revoked_at` (empty until logged out). `refresh_token_hash` is unique, and `user_id` has an index. This is where the 7-day "long pass" from T10 will live.
  5. Alembic setup inside `backend/`: `alembic init migrations`, then wire `migrations/env.py` to `Base.metadata` and to `DATABASE_URL` from config.py (never a password inside `alembic.ini`).
  6. First migration: `alembic revision --autogenerate -m "create users and sessions"`. Adithya reads the generated file with Claude Code before running `alembic upgrade head`.
  7. Check in psql: `\dt` lists `users`, `sessions` and `alembic_version`; `\d users` shows the columns.
  8. `GET /health/db` in main.py: runs `select 1` through `get_db` and returns `{"database": "ok"}`.
- **Added during the task:** a 5-second `connect_timeout` in db.py so `/health/db` fails clearly instead of hanging. Note: a Windows PostgreSQL install also uses port 5432; keep it stopped while Parley runs.
- **Not in this task:** passwords, hashing, tokens, sign-up or log-in routes (T10); tests that need the database (T11 sets up a test database in CI).
- **Done when:** `alembic upgrade head` creates both tables, `\dt` shows them, `/health/db` returns ok while `db` runs (and fails clearly when it's stopped), `pytest` still passes, and Adithya has filled in "In my words".

Questions to ask Adithya (one per big idea): what an ORM is, what a migration is and why not just create tables by hand, why UUIDs for ids, why we store a hash of the refresh token instead of the token itself.

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
- [ ] T9. First tables with SQLAlchemy and Alembic: users, sessions
- [ ] T10. Sign up and log in: hashed passwords, short and long passes (tokens)
- [ ] T11. GitHub Actions: run the tests on every pull request (CI has no `.env`, so set `DATABASE_URL` there and start a Postgres service)
- [ ] T12. Connect the sign-up and log-in screens to the real backend

### Phase 3: Messages over HTTP
- [ ] T13. Chat tables: chats, chat members, messages (per-chat numbers, message IDs). The brief must explain how two messages sent at the same moment never get the same number (a lock or a counter column)
- [ ] T14. Send a message and load history, 30 at a time
- [ ] T15. Connect the chat list and conversation screens to real data

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
- [ ] T26. Nginx in front of several backend copies

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