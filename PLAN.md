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

### Task 11: GitHub Actions runs the tests on every pull request (teaching mode, short)
- **Branch:** `chore/ci`
- **Goal:** every pull request gets a green tick (all checks passed) or a red cross (something broke), before you merge. Also, the first real tests for the sign-up and log-in routes, using a separate test database.
- **Mode:** teaching mode, short explanations, simple pictures.

**The idea in one picture:**
```
 You push a branch / open a PR
        │
        ▼
 GitHub starts a fresh, empty Linux computer (a "runner")
        │
        ├── job "backend":  start Postgres (a "service container")
        │                   install Python packages
        │                   alembic upgrade head   (build the sheets in an empty test database)
        │                   pytest                 (all tests, including the new route tests)
        │
        └── job "frontend": npm ci → npm run lint → npm run build
        │
        ▼
 Green tick ✓ on the PR = safe to merge.  Red cross ✗ = fix first.
```
The runner has no `.env`, so the workflow file gives it test-only values (a throwaway `DATABASE_URL` and `JWT_SECRET`). These are fake and safe to commit.

**Steps:**
1. **A separate test database on your laptop** (so tests never touch your own data):
   - `docker compose exec db createdb -U <your user> parley_test`
   - Add `TEST_DATABASE_URL` to `.env` (same as `DATABASE_URL` but ending in `/parley_test`) and a placeholder to `.env.example`.
2. **`backend/tests/conftest.py`**: before the app loads, point `DATABASE_URL` at `TEST_DATABASE_URL`. Build the tables once with Alembic at the start of the test run. Empty the `users` and `sessions` sheets after each test, so every test starts clean.
3. **`backend/tests/test_auth_routes.py`**: tests through the real routes:
   - sign-up gives 201, and the same email again gives 409;
   - wrong password and unknown email both give 401;
   - `/auth/me` works with the token and gives 401 without it;
   - refresh works with the cookie;
   - after log-out, refresh gives 401.
4. **`.github/workflows/ci.yml`**: runs on every pull request to `main` and every push to `main`. Two jobs:
   - `backend`: Postgres 17 service with a health check, Python 3.13, pip install from `backend/requirements.txt`, test-only `DATABASE_URL` / `TEST_DATABASE_URL` / `JWT_SECRET`, then `alembic upgrade head` and `pytest`.
   - `frontend`: Node 24, `npm ci`, `npm run lint`, `npm run build` in `frontend/`.
   - Use the current major versions of the official actions (`actions/checkout`, `actions/setup-python`, `actions/setup-node`), checked in their docs, and turn on their dependency caches.
5. **Prove it works:** open the PR and wait for the green tick. Then push one commit that breaks a test on purpose, see the red cross, and revert it.
6. **Optional:** on GitHub, Settings → Branches, require the checks to pass before merging, if your plan allows it on a private repo. If not, the rule is simple: never merge a red PR.

- **Not in this task:** deploying anything, Docker images (T25), frontend tests.
- **Done when:** `pytest` passes locally against `parley_test`, your own database is untouched, the PR shows a green tick for both jobs, the deliberate break showed a red cross, and Adithya has filled in "In my words".

Questions for Adithya (short): what CI is and why teams use it; why tests use their own database; why the fake secrets in the workflow file are safe to commit.

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
- [ ] T11. GitHub Actions: run the tests on every pull request (CI has no `.env`, so set `DATABASE_URL` and `JWT_SECRET` there and start a Postgres service)
- [ ] T12. Connect the sign-up and log-in screens to the real backend (only one refresh at a time per tab, other requests wait for it; if a refresh gets 401, wait a moment and retry once, since another tab may have just rotated the cookie; use a Vite proxy so the cookie works)

### Phase 3: Messages over HTTP
- [ ] T13. Chat tables (start the brief with the table map): chats, chat members, messages (per-chat numbers, message IDs). The brief must explain how two messages sent at the same moment never get the same number (a lock or a counter column)
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