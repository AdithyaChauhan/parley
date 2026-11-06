# Parley: Project Plan

Parley is a real-time chat web app, like WhatsApp Web. It's a portfolio project to learn and show backend system design.

**How to use this file**
- One task at a time. Each task = one branch = one pull request.
- "You are here" shows the current task and its brief.
- After Claude Code's report, Adithya pastes its planner block into the planning chat. The planner sends back PLAN.md and DECISIONS.md (box ticked, the next brief in "You are here"). Adithya replaces them before committing, so they go in the same PR.
- Only the planner (chat Claude) writes task briefs. Claude Code never edits this file. It can only suggest changes.
- Adithya may write a file himself if he wants. He tells Claude Code, so it knows.
- CI must pass before merging (main's ruleset enforces it). Claude Code finds the CI and deploy run links itself (the repo is public) and puts them in its after-merge block.
- `/docs` checks with two people: for each person, log in, paste the token into Authorize, confirm with `GET /api/auth/me`, then do their steps.
- npm audit's "braces" warnings: dev-only and no fixed version yet. Don't raise them again until a fix exists.
- Never commit straight to `main`. Even a small fix goes through a branch and a PR (D13).
- When opening the PR, paste the PR description. Proof steps (like a test that fails before the fix) are run locally by Claude Code, with the output in its report.
- Test devices: a Windows laptop (Chrome, Edge) and an iPhone (Safari, Chrome). There is no Android, so briefs ask for "a phone".
- Phone testing over the laptop's Wi-Fi IP (`http://192.168.x.x:5173`) is plain http, so sending (`crypto.randomUUID`), service workers and push don't work there. Use it for layout only, and test sends and push on the live site.
- **Build mode (from Nov 4, 2026, CLAUDE.md):** Claude Code builds, checks and writes up each task end to end, including LEARNING.md and a draft "In my words" (marked as a draft). Adithya reviews when he has time, runs the Git steps, and approves anything on AWS or anything that costs money. Briefs no longer ask him for checks, except iPhone checks on UI tasks.

---

## You are here

### T32. Run Parley on local Kubernetes (build mode)
- **Branch:** `feature/local-kubernetes`
- **Goal:** all of Parley runs on a Kubernetes cluster on the laptop, with one command to start it and one to remove it. Then show what Kubernetes adds: it restarts a stuck copy by itself (D34), replaces a deleted pod, rolls out a new version with nothing lost, and keeps the data when a pod restarts.
- Local only: nothing on AWS, no cost. Production stays on Docker Compose (D30, D31). The setup choices are in D35.

**What runs (namespace `parley`)**
- `backend`: a Deployment with 2 replicas (D28). `COPY_NAME` is the pod name, so `/api/health` and `hello` show which pod answered.
- `worker` and `web`: Deployments with 1 replica each.
- PostgreSQL, Redis and RabbitMQ: StatefulSets with one replica and a volume each, using the same pinned images as Compose.
- `migrate`: a Job that finishes before the backends start or roll.
- The front door is `web`'s Nginx on `http://localhost:8090` (not 8080, so it's never mixed up with Compose). Live lines must still spread over both backend pods, and a stopped pod's lines must move to the other within seconds (D28). For example, use a headless Service with D28's `upstream ... resolve` and `least_conn`, or a normal Service. Pick by measuring the spread.
- Settings go in a ConfigMap. Secrets go in a Secret that a script makes from `.env`, never committed. Resource requests and limits come from measured use.

**Health and updates**
- Every part has readiness and liveness probes. The backend's liveness probe uses `/api/health` (a `def` route, D34) and must not depend on Redis or RabbitMQ (D24). Heavy checks run every 30 s (D27).
- A new backend version rolls one pod at a time with no gap (`maxUnavailable: 0`). If requests reach a stopping pod, add a short pause before it stops.

**Scripts and CI**
- `deploy/k8s/up.sh` creates the cluster if needed, builds and loads the images (tagged with the commit), applies the manifests and waits until everything is ready. `deploy/k8s/down.sh` deletes the cluster. Both run in Git Bash on Windows.
- A new CI job, `k8s`, builds the images, starts kind, applies the manifests, waits until ready, then checks health and one send end to end. Don't make it a required check yet.

**Demos (Claude Code runs them; results go in `docs/kubernetes.md`)**
1. Two users chat through `localhost:8090`: send, ticks, live push, online.
2. At least 20 live lines (a few test users with several lines each, within D24's limits) split over both backend pods.
3. Delete a backend pod mid-chat. Its lines move to the other pod within seconds, nothing is lost, and a new pod starts.
4. A stuck copy restarts by itself. Freeze one backend pod's process (for example with SIGSTOP from the kind node). The liveness probe fails, Kubernetes restarts the pod, and its lines move to the other pod. Record how long that took.
5. A rolling update under light load (~5 msg/s): 0 lost, and afterwards every answer shows the new version.
6. Stop Redis for a minute (scale it to 0). The backends stay up and aren't restarted (D24), and the lines come back afterwards.
7. Delete the PostgreSQL pod. It comes back with the same data.

**Memory:** WSL has ~3.4 GB. Stop the Compose stack while the cluster runs (dev data stays in its own volume), and put it back afterwards (CLAUDE.md).

**Not in T32:** EKS (T33), monitoring inside the cluster, and autoscaling (Later list).

- **Done when:**
  - `up.sh` brings Parley up from nothing, and `down.sh` removes it all.
  - The 7 demos pass and are written up in `docs/kubernetes.md`, with a table mapping each Compose service to its Kubernetes object.
  - CI is green, including the new `k8s` job.
  - The dev stack is back as it was.
  - LEARNING.md has the section with a draft "In my words".

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
- [x] T30. Prometheus metrics and a Grafana dashboard
- [x] T31. Load test with 1,000 fake users; write up the results with the laptop's specs (with least_conn, judge the spread of open live lines, not request counts) (include 1,000 users connecting at once, to check the per-copy subscribe lock from D23)
- [x] Fix: Parley under load: a thread/connection deadlock, and the password-check cap (D34)

### Phase 10: Kubernetes
- [ ] T32. Run Parley on local Kubernetes (with liveness probes, so a stuck copy restarts by itself, D34, D35)
- [ ] T33. Optional, only if ready before the AWS free plan ends (Feb 2, 2027, or when the credits run out): short EKS run with Terraform, and record a demo. Tear it all down the same day with `terraform destroy` (the cluster costs money every hour)

### Phase 11: Show it
- [ ] T34. README with an architecture diagram, screenshots, a demo video and the load-test results, plus a short "How I built this" section (planned with Claude, coded with Claude Code; Adithya made the decisions and reviewed the work; up to T31 he also tested every change himself, and from the load fix on (build mode) Claude Code ran the checks; LEARNING.md shows what he learned). First re-run load tests b and d with other apps closed, for clean numbers (the Nov 6 runs had Windows paging)

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
- Small: a page reload during overload shows the log-in screen when its refresh gets a 503. Wait for `Retry-After` and try again instead.
- More capacity, if ever needed (the limit is now about one core per copy): a third copy, autoscaling on Kubernetes (HPA), or `uvicorn[standard]`. A cheaper refusal (for example in Nginx) could also stop accepted messages falling past the limit. None of these is measured yet.