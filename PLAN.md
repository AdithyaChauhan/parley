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
- Test devices: a Windows laptop (Chrome, Edge) and an iPhone (Safari, Chrome). There is no Android, so briefs ask for "a phone".
- Phone testing over the laptop's Wi-Fi IP (`http://192.168.x.x:5173`) is plain http, so sending (`crypto.randomUUID`), service workers and push don't work there. Use it for layout only, and test sends and push on the live site.
- Each task's "Done when" also needs the task's "In my words" in LEARNING.md filled in by Adithya. For frontend tasks (fast mode, see CLAUDE.md), Claude Code drafts it and Adithya just reviews it.

---

## You are here

### Task 30: Metrics with Prometheus and a Grafana dashboard (teaching mode, friend style)
- **Branch:** `feature/metrics`
- **Goal:** one dashboard that shows what Parley is doing right now: requests per second, how fast they are, errors, open live lines per copy, messages sent, notification outcomes, queue depth, and how hard each container is working. T31's load test reads its numbers from here.
- **Mode:** teaching mode (example first, short, "In my words" at the end), with recaps. Claude Code runs the long checks. It works on the laptop first (D29). Nothing new is opened to the internet.

**Example first (Claude Code shows this before any code):**
```
 every 15 s, Prometheus asks each part "what are your numbers?" (a "scrape")
   backend_a:8000/metrics  → http_requests_total{route="/api/chats/{id}/messages",status="201"} 1532
   backend_b:8000/metrics  → live_lines_open 7
   worker:9100/metrics     → notify_jobs_total{outcome="sent"} 41, {outcome="skip: already read"} 230
   postgres / redis exporters, RabbitMQ's built-in metrics, cAdvisor (CPU and memory per container)
 Prometheus keeps the numbers over time → Grafana draws them:
   ┌ requests/s by copy ┐ ┌ p95 latency ┐ ┌ open live lines A|B ┐ ┌ queue: notify / failed ┐
```
- A **counter** only goes up (requests, messages). A **gauge** goes up and down (open live lines). A **histogram** puts timings into buckets, so you can read p50, p95 and p99. p95 = 95% of requests were faster than this.
- **Labels** split one number into groups (by route, status, copy). Routes use their template (`/api/chats/{id}`), never the real id, or the number of groups explodes.

**Steps:**
1. **Backend metrics** with the official `prometheus-client` (pinned), plus a small middleware we write ourselves:
   - `http_requests_total` and a request-duration histogram, by method, route template and status.
   - `live_lines_open` (gauge).
   - `messages_sent_total`.
   - Pushes published and received through Redis pub/sub.
   - 429s by limit rule.
   - Served at `/metrics` on port 8000. Nginx passes only `/api/` on, so `/metrics` is never reachable from outside. Test that.
2. **Worker metrics** on its own port (9100): jobs by outcome (`sent`, each skip reason, `failed`, `parked`) and retries.
3. **Exporters:** `postgres_exporter`, `redis_exporter`, RabbitMQ's built-in Prometheus metrics (check whether the plugin is already on), and cAdvisor (CPU and memory per container, which T31 needs).
4. **Prometheus + Grafana** in Compose, under their own `monitoring` profile (`docker compose --profile app --profile monitoring up`). Images are pinned to exact tags (D27).
   - Grafana is reachable only on the laptop (`127.0.0.1:3000`), and its admin password comes from `.env`.
   - The data source and the dashboard are **files in the repo** (provisioning), so the dashboard rebuilds itself on any machine.
   - Prometheus keeps 7 days of data.
5. **The dashboard (one page):**
   - Requests/s by copy
   - Latency p50 / p95 / p99
   - 5xx error rate and 429s
   - Open live lines per copy
   - Messages per minute
   - Notification outcomes
   - Queue depth (`notify`, `notify.failed`)
   - Postgres connections
   - Redis memory and commands/s
   - CPU and memory per container
6. **The server (decide after measuring):** check memory on the server with the monitoring stack. If it fits next to Parley (with swap barely used), run it there too, reachable only through **Session Manager port forwarding** (no new public port). Otherwise, the server runs only the metrics endpoints, and the dashboard stays on the laptop. Claude Code measures, then proposes.
7. **Tests:**
   - `/metrics` shows the counters, and a request moves them.
   - Routes are labelled by template.
   - `/metrics` through Nginx doesn't return metrics.
   - The worker's counter moves for a skipped job.
   - CI's containers job checks that both copies answer `/metrics` inside the network.
- **Not in this task:** alerts in Grafana (CloudWatch already emails, D31), tracing, log search.
- **Done when:**
  - `docker compose --profile app --profile monitoring up` on the laptop, and Grafana at `localhost:3000` shows the dashboard by itself.
  - Chatting between two windows moves the numbers: requests, messages, open live lines per copy, and notification outcomes.
  - Stopping `backend_a` shows on the dashboard (its line drops and B takes the live lines).
  - `/metrics` isn't reachable through Nginx (locally or on the live site).
  - The server decision from step 6 is made and written down.
  - All tests pass, CI is green (run link in the report), and "In my words" is filled in by Adithya.

"In my words" prompts: what Prometheus does every 15 seconds; counter vs gauge vs histogram; what p95 means and why it matters more than the average; why route labels use the template and not the real id.

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
- [x] T26. Nginx in front of several backend copies (T25 already puts one Nginx in front of one copy, with real-IP headers) (demo: stop one copy mid-chat and the apps reconnect to the other through Nginx, with nothing lost) (turn on `secure=True` for the refresh cookie once HTTPS is on)
- [x] T27. Responsive layout fix, and hide buttons that do nothing yet (fast mode), before going live: four columns from 1280 px, the side panel in the chat's place at 768-1279 px, one screen at a time under 768 px (D8)

### Phase 8: Go live
- [x] T28. Live on AWS: one EC2 server built with Terraform, HTTPS, the generic server setup (works on any Linux server, D29)
- [x] Fix: phone keyboard layout (PR #29)
- [x] Before sharing the link: a fresh, empty database on the server (removes the test accounts), then sign up clean demo accounts (done in T29, step 0)
- [x] T29. Auto-deploy from GitHub: images built in CI and pushed to ECR, deployed through OIDC + SSM (no stored AWS keys, no SSH), secrets in SSM Parameter Store, and a CloudWatch alarm with logs. Notes from T28: SSM commands run as root while `/opt/parley` belongs to ssm-user, so git needs `safe.directory` (or run as ssm-user); restart the backend copies one at a time on a deploy (a full `deploy.sh` restarted both together); builds move from the server to CI; backups are still a known gap.

### Phase 9: Measure it
- [ ] T30. Prometheus metrics and a Grafana dashboard
- [ ] T31. Load test with 1,000 fake users; write up the results with the laptop's specs (with least_conn, judge the spread of open live lines, not request counts) (include 1,000 users connecting at once, to check the per-copy subscribe lock from D23)

### Phase 10: Kubernetes
- [ ] T32. Run Parley on local Kubernetes
- [ ] T33. Optional, only if ready before the AWS free plan ends (Feb 2, 2027, or when the credits run out): short EKS run with Terraform, and record a demo. Tear it all down the same day with `terraform destroy` (the cluster costs money every hour)

### Phase 11: Show it
- [ ] T34. README with an architecture diagram, screenshots, a demo video and the load-test results, plus a short "How I built this" section (planned with Claude, coded with Claude Code; Adithya made the decisions, reviewed and tested every change; LEARNING.md shows what he learned)

### Later
- End-to-end encryption phase: 1:1 text, one device, safety numbers (see D12) (chat-list previews then move to the app, since the server can't read the text)
- v2, in this order: groups (one message fans out to many people), images and documents (S3-style storage: MinIO in Docker Compose by default, AWS S3 when configured, D29), voice notes, reactions (these bring back the emoji button), edit and delete, search (only for your own messages on your device, D12). Groups bring back the "..." menu ("New group") and the group members view.
- Maybe later: Status (24-hour stories, which bring back the eye icon: a good topic for expiry and fan-out), voice and video calls (WebRTC, a big topic on its own, which bring back the calls icon).
- Not planned: Dashboard, Tasks and Stats (they came from the reference design, not from WhatsApp), the "available" pill, and contacts sync.
- Optional: move notifications into their own service
- Small phone polish, only if wanted: a slimmer phone chat header (plain back arrow, 32 px avatar, 18 px name, 56 px tall). UI/UX polish isn't a priority.
- Small: a paths filter in `deploy.yml` so docs-only merges skip the deploy (today every merge deploys, safely, one copy at a time).
- Small: two Tailwind "canonical class" warnings in `ChatScreen.tsx` (style tips; lint and build pass).
- Re-check: the backend's 4 high scan findings (glibc, zlib) wait for a Debian fix. Look again at the next Python patch.
- Small: a hint near "Turn on notifications" (it lives only in the gear menu and is easy to confuse with the browser's own site toggle).