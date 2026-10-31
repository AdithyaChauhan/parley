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

### Task 29: Auto-deploy from GitHub, secrets in AWS, and an alarm (teaching mode for the infra, friend style)
- **Branch:** `feature/auto-deploy`
- **Goal:** after a merge to `main`, GitHub builds the images, stores them in AWS (ECR), and updates the server by itself, one backend copy at a time, so chats keep working during a deploy. The server's secrets live in AWS Systems Manager Parameter Store instead of only in a file. If the server breaks, you get an email.
- **Mode:** teaching mode for the infra (example first, short, "In my words" at the end), with recaps. **Anything that creates or changes AWS resources waits for Adithya's OK on the plan, including the cost** (CLAUDE.md). Secrets never pass through a chat.

**Step 0, before the task (Claude Code gives the exact commands, and Adithya confirms before anything is deleted): a fresh database on the server.**
- Wipe the test accounts and chats (an empty database volume, then `migrate` builds the tables again), and clear Redis.
- Then sign up clean demo accounts (for example "Ana" and "Ben") with new passwords.
- After this, the link can go on the resume.

**Example first (Claude Code shows this before any code):**
```
 you merge a PR into main
   → GitHub Actions: tests pass (CI) → build parley-backend + parley-web, tagged with the commit (e.g. a410b04)
   → log in to AWS with OIDC (a short-lived pass, no AWS keys stored in GitHub)
   → push both images to ECR (AWS's private image store)
   → SSM "send command" to the server (no SSH): run deploy/aws/deploy-from-ecr.sh a410b04
 on the server:
   fetch secrets from Parameter Store → write .env (chmod 600)
   pull the two images from ECR → migrate → restart backend_a → wait healthy → restart backend_b → wait healthy → worker → web
   /api/health now says "version": "a410b04"
 if the server's health checks fail → CloudWatch alarm → email to you
```
- **OIDC** means GitHub proves "I am the parley repo, on main" to AWS, and AWS hands it a pass that lasts minutes. There are no long-lived keys that could leak.
- **ECR** is a private Docker Hub inside your AWS account.
- **Parameter Store** is a locked box for secrets in AWS. The server reads it with its own role.

**Steps:**
1. **Terraform** (`deploy/aws/terraform/`, plan → your OK → apply):
   - Two ECR repositories (`parley-backend`, `parley-web`), with a rule that keeps only the last 10 images.
   - The GitHub OIDC provider, plus a role GitHub can use **only from `AdithyaChauhan/parley` on `main`**. It may only push to those two repositories and send commands to this one server.
   - Add to the server's role: pull from those two repositories, read `/parley/prod/*` from Parameter Store, and write container logs to CloudWatch.
   - CloudWatch: a log group with 7-day retention, an alarm on the server's status checks (and high CPU for 15 minutes), and an SNS email to you. You click "Confirm subscription" in the email once.
2. **Secrets into Parameter Store:** a one-time script you run **on the server** reads the current `.env` and stores each value as a SecureString under `/parley/prod/`. The values never show on screen and never leave AWS.
3. **`deploy/aws/deploy-from-ecr.sh`** (AWS-only, D29):
   - Fetch the parameters, write `.env` (600), and log in to ECR.
   - Pull the given tag, run `migrate`, then restart **one copy at a time**, waiting for healthy each time (a rolling restart), then the worker, then web.
   - It runs as the repo owner, not root, to avoid git's "dubious ownership" error from T28.
   - A small Compose file in `deploy/aws/` swaps `build:` for the ECR `image:`.
4. **`.github/workflows/deploy.yml`:** it runs on push to `main` only **after CI passes**, and can also be started by hand with a version tag (that's the rollback). It builds, pushes to ECR, sends the SSM command, waits, and fails the run if the server doesn't come back healthy.
   - GitHub stores only **variables** (role ARN, region, instance id), no secrets.
5. **Version in `/api/health`:** the image gets `APP_VERSION` (the commit) at build time, so you can see which version is live.
6. **The generic path stays (D29):** `deploy/server/deploy.sh` with a plain `.env` still works on any server.
   - `deploy.sh` now refuses to run anywhere except `/opt/parley`. It got run on the laptop by mistake after T28.
7. **Small leftover from the phone keyboard fix:** add the desktop spot-check line to LEARNING.md's "Checked" list.

- **Cost** (Claude Code checks the real prices and shows them with the plan): ECR storage and CloudWatch logs are cents a month, SNS email and Parameter Store standard are free. The server cost doesn't change.
- **Not in this task:** a load balancer, several servers, blue/green deploys, and backups (still a known gap).
- **Done when:**
  - The fresh database is done, and clean demo accounts work on the live site.
  - Merging a small change to `main` deploys by itself: the Actions run is green, and `/api/health` shows the new version.
  - **During a deploy, a chat between the laptop and the iPhone keeps working.** Lines reconnect to the other copy, and nothing is lost.
  - GitHub has **no AWS keys** (only variables), and the role only works from this repo on `main`.
  - `.env` on the server is rebuilt from Parameter Store, and the laptop's plain `.env` path still works (D29).
  - Container logs show in CloudWatch, and a test alarm (`set-alarm-state`) sends you an email.
  - Rollback: running the workflow by hand with the previous version puts it back, which `/api/health` confirms.
  - All tests pass, CI is green (run links in the report), and "In my words" is filled in by Adithya.

"In my words" prompts: how GitHub gets into AWS without a stored key (OIDC); why the copies restart one at a time; where the secrets live now and who can read them; what happens when the alarm fires.

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
- [ ] Before sharing the link: a fresh, empty database on the server (removes the test accounts), then sign up clean demo accounts (step 0 of T29)
- [ ] T29. Auto-deploy from GitHub: images built in CI and pushed to ECR, deployed through OIDC + SSM (no stored AWS keys, no SSH), secrets in SSM Parameter Store, and a CloudWatch alarm with logs. Notes from T28: SSM commands run as root while `/opt/parley` belongs to ssm-user, so git needs `safe.directory` (or run as ssm-user); restart the backend copies one at a time on a deploy (a full `deploy.sh` restarted both together); builds move from the server to CI; backups are still a known gap.

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
- Small: a hint near "Turn on notifications" (it lives only in the gear menu and is easy to confuse with the browser's own site toggle).