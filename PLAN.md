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

### Task 26: Two backend copies behind Nginx, and a failover demo (teaching mode, friend style)
- **Branch:** `feature/two-copies-nginx`
- **Goal:** Nginx spreads users across two backend copies, A and B. If one copy dies mid-chat, the people on it reconnect to the other within seconds, and nothing is lost. This is the demo for the README video.
- **Mode:** teaching mode, friend style, with recaps. Claude Code runs the repeated and timed checks. Adithya does the browser demo.

**Example first (Claude Code shows this before any code):**
```
 browser → Nginx :8080 ─┬─→ backend_a (COPY_NAME=A)
                        └─→ backend_b (COPY_NAME=B)      both share db, redis, rabbitmq
 GET /api/health ×6 → A, B, A, B, A, B                    (spread out)
 Ana's live line → A,  Ben's live line → B               (any copy works: tickets and pushes are in Redis, T21)

 docker compose stop backend_a   (mid-chat)
   Ana's line closes → "Reconnecting..." → new ticket → Nginx skips A → line on B (a few seconds)
   Ana's waiting message goes out once (client_msg_id), and catch-up fills any gap
   Ben notices nothing
 docker compose start backend_a  → new lines can land on A again
```
- **No "sticky sessions":** with sticky sessions, Ana would be tied to one copy. We don't need them, because nothing about Ana lives inside a copy's memory. It's all in PostgreSQL and Redis.

**Steps:**
1. **Compose:**
   - Replace `backend` with `backend_a` and `backend_b`. They share the T25 block, differ only in `COPY_NAME`, and have the same health check.
   - `web` waits for both to be healthy.
   - `migrate` still runs once, before both (D27).
2. **`nginx.conf`:**
   - An `upstream` with both copies, `least_conn` (the next line goes to the copy with fewer open connections, which suits long-lived live lines), and `max_fails=1 fail_timeout=10s`, so a dead copy is skipped for 10 s.
   - Keep T25's "find new container addresses" behaviour for upstream servers. Use the `resolve` option on the upstream servers with a shared `zone`, and check our Nginx version supports it.
   - Short `proxy_connect_timeout` (about 2 s).
   - `proxy_next_upstream` retries on connection errors and timeouts, but only for requests that are safe to repeat. Nginx's default is to never retry a POST once it's been sent, and we keep that: a repeated log-in or refresh could clash with token rotation. Sends are safe anyway, because the app re-sends with the same `client_msg_id`.
3. **Clean stop:** when a copy gets SIGTERM, its live lines close quickly with a "going away" code, so apps reconnect at once rather than after the 10 s grace period. Check what uvicorn does today and show it.
4. **App (fast mode):** the `hello` event carries the copy name, and the app logs "live line on copy B" in the browser console. That's for the demo and debugging only, with nothing new on screen.
5. **Refresh cookie:** a `COOKIE_SECURE` setting (default `false`). T26b turns it on with HTTPS.
6. **Chore:** pin CI's test-job Postgres to `postgres:17.11` (D27).
7. **CI containers job:** starts both copies and checks that `/api/health` through Nginx answers from both A and B.
8. **Tests:** backend tests don't change much: the copies are the same code. Add a test that `COOKIE_SECURE` sets the cookie's `Secure` flag. Claude Code proves the rest with commands (below).
- **Claude-run checks:**
  - 10 × `/api/health` shows both A and B.
  - Stop A, and every request goes to B with no errors after the first few seconds.
  - Start A again, and it gets traffic again.
  - 25 quick sends spread across both copies still hit the 20-per-10-s limit (the limits live in Redis).
  - A copy stopping closes its lines in about a second, not 10.
- **Not in this task:** HTTPS (T26b), more than two copies, Nginx itself failing (there's one Nginx; in the cloud a load balancer does this job).
- **Done when:**
  - `docker compose --profile app up --build`: backend_a and backend_b are both healthy.
  - Ana (Chrome) and Ben (Edge) chat at :8080, and the browser consoles show which copy each is on.
  - **Failover demo:** stop the copy Ana is on in the middle of a chat. Ana shows "Reconnecting..." and is back within a few seconds on the other copy. A message she sends during it arrives once. Ben keeps chatting with no problem. Start the copy again, and all is fine.
  - The Claude-run checks above pass, with output shown.
  - All tests pass, CI is green (run link in the report), and "In my words" is filled in by Adithya.

"In my words" prompts: why Parley doesn't need sticky sessions; what Nginx does when a copy dies (skip it, try the other); why Nginx doesn't retry a POST, and why our sends are safe anyway; why the rate limit still works across two copies.

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
- [x] T25. Dockerfiles and Docker Compose for every part (the worker gets its own container; the backend and worker start only once PostgreSQL, Redis and RabbitMQ are healthy, since the backend can't start while Redis is down) (the worker needs a SIGTERM handler, since `docker stop` sends SIGTERM, not Ctrl+C)
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