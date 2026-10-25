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

### Task 25: Every part in a container (Dockerfiles + Docker Compose) (teaching mode, friend style)
- **Branch:** `feature/containers`
- **Goal:** one command starts all of Parley: database, Redis, RabbitMQ, migrations, backend, worker, and the app served by Nginx. You open one address, http://localhost:8080. Your normal dev setup (uvicorn + Vite on your laptop) keeps working too.
- **Mode:** teaching mode, friend style, with a recap every few steps. Long or repeated checks are run by Claude Code itself (CLAUDE.md).

**Example first (Claude Code shows this before any code):**
```
 docker compose --profile app up --build
   db       ─┐
   redis    ─┼─ healthy? ──→ migrate (alembic upgrade head, runs once, then exits)
   rabbitmq ─┘                    │ finished OK
                                  ├──→ backend  (uvicorn, port 8000 inside the network only)
                                  └──→ worker   (python -m app.notify.worker)
   web (Nginx) ──→ serves the built app, and passes /api (and the live line) to backend
   browser ──→ http://localhost:8080   ← the only port open to your laptop (plus the DB/Redis/RabbitMQ ones for dev)

 Inside the network, names replace 127.0.0.1:   DATABASE_URL → db:5432, REDIS_URL → redis:6379, ...
```
- An **image** is a frozen box with Python, the code and its packages.
- A **container** is a running copy of an image.
- A **profile** means `docker compose up` alone still starts only the helpers, like today. `--profile app` adds Parley itself.

**Steps:**
1. **`backend/Dockerfile`:**
   - Built on `python:3.13-slim`, pinned to an exact tag (check, don't guess).
   - Install `requirements.txt` first, then copy the code, so a code change doesn't reinstall every package.
   - Run as a non-root user.
   - The default command is uvicorn with `--proxy-headers --forwarded-allow-ips="*"` (see step 4).
   - One image, used for backend, worker and migrate, with a different command for each.
2. **`.dockerignore`** for backend and frontend: skip `.env`, `.venv`, `node_modules`, `dist` and caches. **`.env` must never be inside an image.** Secrets come in at run time from Compose.
3. **`frontend/Dockerfile`:** two stages.
   - Node (an exact LTS tag) runs `npm ci` and `npm run build`.
   - `nginx` (an exact stable tag) serves `dist`.
4. **`frontend/nginx.conf`:**
   - Any unknown path falls back to `index.html`, so `/login` works after a reload.
   - `/api` is passed to `backend:8000`, with the WebSocket upgrade headers for `/api/live` and a read timeout well above the 25 s ping (D21).
   - `sw.js` is sent with `Cache-Control: no-cache`, so a new service worker is picked up.
   - `X-Forwarded-For` is set to `$remote_addr` (overwritten, not appended), so a client can't fake its IP.
   - The backend's port isn't open to the laptop, so only containers on Parley's network can reach it. That's why trusting forwarded headers from any address there is OK, and the rate limits (D24) see the real browser IP.
5. **`docker-compose.yml`:**
   - Add `migrate`, `backend`, `worker` and `web` under the `app` profile.
   - Health checks:
     - PostgreSQL: `pg_isready`
     - Redis: `redis-cli ping`
     - RabbitMQ: T23's check
     - Backend: `/api/health` (checked with Python, since slim has no curl)
   - Start order uses `depends_on` with `service_healthy`, and `service_completed_successfully` for migrate.
   - Values come from `.env`, but hostnames are the service names.
   - `stop_grace_period`: 15 s for the worker and 10 s for the backend.
6. **Worker:** add a SIGTERM handler (`docker stop` sends SIGTERM) that takes the same clean "finish or return the job, then Stopped" path as Ctrl+C.
7. **CI:**
   - A new job builds both images.
   - It starts the whole stack with `docker compose --profile app up -d --wait`, using a throwaway `.env` made from `.env.example` with dummy values.
   - It checks `http://localhost:8080/api/health` through Nginx, then shuts it all down.
   - The existing test job stays as it is.
- **Not in this task:** a second backend copy and failover (T26), HTTPS (T26 and T26b), pushing images to a registry.
- **Done when:**
  - `docker compose --profile app up --build` starts everything. `migrate` runs once and exits 0, and the rest show "healthy".
  - At http://localhost:8080, Ana (normal window) and Ben (Edge) can sign up, chat live, see ticks and typing, and the browser notification still arrives. The worker's log is in `docker compose logs worker`.
  - Reloading on `/login` still works (SPA fallback).
  - `docker compose restart backend`: both apps show "Reconnecting...", then come back, and nothing is lost.
  - `docker compose stop worker` prints the clean "Stopped" line (SIGTERM).
  - The backend log shows the browser's IP, not Nginx's.
  - `.env` isn't inside either image (Claude Code shows the check).
  - `docker compose up` (no profile), plus uvicorn and Vite on the laptop, still works as before.
  - All tests pass, CI is green (run link in the report), and "In my words" is filled in by Adithya.

"In my words" prompts: what the difference is between an image and a container; why migrations run in their own one-shot container instead of inside each backend copy; how Nginx lets the backend see the real IP, and why a client can't fake it.

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
- [x] T24. Browser push notifications (Web Push). Push text must not contain message text (see D12). Web Push needs HTTPS (localhost counts); check again at T26

### Phase 7: Run it like production
- [ ] T25. Dockerfiles and Docker Compose for every part (the worker gets its own container; the backend and worker start only once PostgreSQL, Redis and RabbitMQ are healthy, since the backend can't start while Redis is down) (the worker needs a SIGTERM handler, since `docker stop` sends SIGTERM, not Ctrl+C)
- [ ] T26. Nginx in front of several backend copies (T25 already puts one Nginx in front of one copy, with real-IP headers) (demo: stop one copy mid-chat and the apps reconnect to the other through Nginx, with nothing lost) (turn on `secure=True` for the refresh cookie once HTTPS is on)

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