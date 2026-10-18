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

### Task 8: FastAPI app, health check, PostgreSQL in Docker Compose (teaching mode)
- **Branch:** `feature/backend-setup`
- **Goal:** the first piece of the backend. A tiny FastAPI app that answers "I'm alive", a PostgreSQL database running in Docker, and the first test. Nothing talks to the database yet (that's T9).
- **Mode:** full teaching mode (CLAUDE.md "While building"). This is the part Adithya explains in interviews.
- **How the pieces fit:**
```
 Browser / curl ──HTTP──> FastAPI app (backend/, runs on your laptop, port 8000)
                              GET /health -> {"status": "ok"}

 Docker Compose ──runs──> PostgreSQL (container "db", port 5432)   <- T9 connects the app to it

 pytest ──calls──> the FastAPI app in memory (no server needed)
```
- **Steps:**
  1. Check the tools: Python 3.12 or newer (`python --version`), Docker Desktop installed and running (`docker --version`, `docker compose version`). If one is missing, Claude Code gives install steps and waits.
  2. `backend/` folder with a virtual environment (`python -m venv .venv`) and `requirements.txt`: fastapi, uvicorn (the server that runs FastAPI), pytest, httpx2 (needed by FastAPI's test client; newer Starlette prefers it over the old httpx). These count as part of D6.
  3. `backend/app/main.py`: the FastAPI app with one route, `GET /health`, that returns `{"status": "ok"}`. Run it with uvicorn and open `http://localhost:8000/health` and `http://localhost:8000/docs`.
  4. `backend/tests/test_health.py`: one pytest test that calls `/health` and checks the answer. Run `pytest`.
  5. `docker-compose.yml` at the repo root: one service, `db`, using the official `postgres` image, with a named volume so data survives restarts, and a health check.
  6. `.env.example` (committed) with the database name, user and password as placeholders; the real `.env` (never committed) is copied from it. Compose reads `.env`.
  7. `.gitignore` at the root: `.venv/`, `__pycache__/`, `.pytest_cache/`, `.env`.
  8. Check Postgres: `docker compose up -d`, `docker compose ps` shows `db` as healthy, and `docker compose exec db psql -U <user> -d <db> -c "select 1;"` prints 1.
- **Agreed changes:** `.gitignore` is written first (before the venv). Also add `backend/app/__init__.py` and `backend/pytest.ini` so plain `pytest` finds the app. Pin `postgres:17` (not `latest`) and exact package versions in `requirements.txt`.
- **Not in this task:** SQLAlchemy, tables, Alembic, any connection from the app to the database, Dockerfile for the backend (T25).
- **Done when:** `/health` returns `{"status": "ok"}`, `pytest` passes, `db` shows healthy, `.env` is not in `git status`, and Adithya has filled in "In my words".

Questions to ask Adithya along the way (one per big idea): what a route is, why a virtual environment, what a Docker container is, why `.env` is never committed.

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
- [ ] T8. FastAPI app with a health check, PostgreSQL in Docker Compose, a first tiny pytest test, and `.gitignore` entries for the Python venv and `.env`
- [ ] T9. First tables with SQLAlchemy and Alembic: users, sessions
- [ ] T10. Sign up and log in: hashed passwords, short and long passes (tokens)
- [ ] T11. GitHub Actions: run the tests on every pull request
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