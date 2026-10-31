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

### Task 28: Parley live on AWS (one EC2 server, Terraform, HTTPS) (teaching mode for the infra, friend style)
- **Branch:** `feature/live-on-aws`
- **Goal:** a real link, like `https://parley-adithya.duckdns.org`, that anyone can open on a laptop or a phone, with a padlock. It runs on one AWS server that Terraform builds from code. The server setup itself is generic: the same files run Parley on any Linux server, with no AWS needed (D29). T29 then adds auto-deploy and monitoring.
- **Mode:** teaching mode for the infra (example first, short, "In my words" at the end), with recaps. Claude Code runs the commands, but **anything that creates, changes or deletes AWS resources waits for Adithya's OK**: it shows `terraform plan` in plain words, including what costs money, and waits for "apply". Same for `destroy`.

**Before the task (Adithya, about 15 minutes):**
1. **AWS console:**
   - Budget alert (done): $30/month, with alerts at 80% actual, 100% forecast and 100% actual. It excludes credits, so it counts real usage.
   - Old delivery-delay Fargate service and cluster in ap-southeast-1 (done): deleted. No CortexAI services or load balancers run anywhere.
2. **AWS CLI on the laptop:**
   - Install the AWS CLI v2 and the Session Manager plugin.
   - Run `aws configure` with an IAM user's access key. The keys stay in `~/.aws`, never in the repo or a chat.
   - Region: `ap-south-1` (Mumbai, closest to you).
3. **Domain:** make a free DuckDNS subdomain (duckdns.org, log in with GitHub), for example `parley-adithya`. The DuckDNS token is a secret: it goes in `.env` only. (A bought domain can replace it later, with no code change.)
4. **Repo visibility:** the server needs to get the code. Before the repo goes public, Claude Code scans the whole Git history for secrets (for example with gitleaks in Docker). If it's clean, Adithya makes the repo public (D13: "public once live chat works"). If not, it stops and reports.

**Example first (Claude Code shows this before any code):**
```
 laptop: terraform apply (after your OK)
   → AWS builds: 1 EC2 server (Ubuntu, 2 GB if the free plan allows) + fixed IP (Elastic IP)
                 + firewall (security group): only 80 and 443 open, no SSH port at all
                 + a role that lets AWS Session Manager in (shell access without SSH keys)
 DuckDNS: parley-adithya.duckdns.org → the fixed IP
 on the server (through Session Manager):
   git clone → write .env (chmod 600) → docker compose -f docker-compose.yml -f docker-compose.prod.yml --profile app up -d --build
   certbot gets a free Let's Encrypt certificate → Nginx serves https, and http → https
 browser → https://parley-adithya.duckdns.org 🔒 → Nginx → backend_a / backend_b → db, redis, rabbitmq (no ports open to the internet)
```
- **Terraform** describes servers in code: `plan` shows what would change, `apply` does it, and `destroy` removes it all.
- **Session Manager** gives a shell on the server through AWS, so there's no port 22 to attack and no key file to lose.

**Steps:**
1. **Measure first:** run `docker stats` on the laptop with the full stack, and report how much memory it uses. That decides the server size. Prefer an x86 server with 2 GB (such as t3.small) if the account's free plan covers it, and say what it costs otherwise. Add a 2 GB swap file either way.
2. **`deploy/aws/terraform/`** (all AWS-only files live under `deploy/aws/`, D29):
   - A small network built by Terraform itself (VPC, one public subnet, internet gateway, route table; all free). The account has no default VPC in Mumbai.
   - A security group with only 80 and 443 in (no 22).
   - EC2 running Ubuntu LTS, with an instance role that has only `AmazonSSMManagedInstanceCore`, and an encrypted 20 GB disk. `user_data` installs Docker and the Compose plugin.
   - An Elastic IP.
   - Outputs: the IP and the instance id.
   - The state file stays local and gitignored (D30). Pin the provider version, and tag every resource `project=parley`.
3. **`docker-compose.prod.yml`** (generic, at the repo root, no AWS inside):
   - Removes the dev ports of db, redis and rabbitmq (`ports: !reset []`, so nothing but Nginx is reachable).
   - `restart: unless-stopped` on every service except `migrate` (a one-shot job).
   - `COOKIE_SECURE=true`.
   - Visitors use ports 80 and 443. The server maps them to 8080 and 8443 inside the container, since Nginx is non-root (D27, D30).
   - Log size limits (`max-size`) so the disk doesn't fill up.
4. **HTTPS:**
   - A production Nginx config (`deploy/server/nginx.prod.conf`, mounted into `web`): port 80 only answers Let's Encrypt's check and redirects everything else to https. Port 443 uses TLS 1.2+ with the certificate, plus the same `/api`, live line and `sw.js` rules as T25/T26.
   - certbot (official image, `v5.8.0`): the **first** certificate comes from `deploy/server/first-cert.sh` (certbot answers port 80 itself for about 30 s, before Nginx starts). **Renewals** use the webroot method through Nginx, proved with a dry run. A deploy hook gives Nginx's group read access to the key. Nginx reloads on a timer so it picks up renewals.
   - Add HSTS only after https is proven to work.
5. **`deploy/server/` scripts (generic, for any Linux server):**
   - `setup.sh` installs Docker, adds swap, and clones the repo.
   - `deploy.sh` pulls, rebuilds and restarts. It uses `--no-deps --build web` for frontend-only changes (D27).
   - `.env.prod.example` lists every value the server needs.
   - Adithya types the real values on the server, through Session Manager. Secrets never pass through a chat.
6. **Push on the live site:** new VAPID keys for production (don't reuse dev's), and `VAPID_SUBJECT` set to a real `mailto:`. Browsers subscribe again on the new site (T24 note).
7. **Real IP:** Nginx is still the only thing in front, so D27's rule holds. Check that the backend logs real visitor IPs, not Docker's gateway.
8. **Docs:** a short `deploy/README.md` covers how to run Parley on any Linux server, how to run it on AWS with Terraform, and how to turn it all off (`terraform destroy`).
- **Not in this task:** auto-deploy, ECR, SSM Parameter Store and CloudWatch (T29), backups (noted as a known gap), iPhone push (it needs the app added to the home screen), and a bought domain.
- **Done when:**
  - https://<your-subdomain>.duckdns.org opens Parley with a valid padlock, and http:// redirects to https.
  - Ana on the laptop (Chrome) and Ben on a **real phone** (Android or iPhone) can sign up, chat live, and see ticks and typing. The phone keyboard problem found here is fixed separately, in the phone keyboard fix right after this task.
  - A browser notification arrives on the laptop (Edge or Chrome) on the live site.
  - In DevTools, the refresh cookie shows `Secure` and `HttpOnly`.
  - Claude Code shows the security group (only 80 and 443), and that ports 5432, 6379, 5672 and 15672 don't answer from the internet.
  - Failover on the server: stop `backend_a` through Session Manager mid-chat, and the app reconnects to B with nothing lost.
  - Claude Code shows the `terraform destroy` plan without running it, and explains how to turn it all off.
  - The CI containers job is still green, so the local run is untouched (D29). The run link is in the report, and "In my words" is filled in by Adithya.

"In my words" prompts: what Terraform plan, apply and destroy do; why there's no SSH port, and how you still get a shell; how Let's Encrypt proves you own the domain, and why http only redirects; why db, Redis and RabbitMQ must have no open ports on a server.

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
- [ ] T28. Live on AWS: one EC2 server built with Terraform, HTTPS, the generic server setup (works on any Linux server, D29)
- [ ] Fix (right after T28, before sharing the link): phone keyboard layout (fast mode, branch `fix/phone-keyboard`). On iPhone the keyboard hid the message box, pushed the chat header off screen, and the page stayed shifted after the keyboard closed. Wanted (WhatsApp behaviour, D8): header fixed at top, message box fixed just above the keyboard (or at the bottom), only the messages scroll; sending jumps to the newest message. Fix 1A: `h-dvh` instead of `h-svh`, viewport meta `interactive-widget=resizes-content` (Android), and a small `visualViewport` listener so iOS sizes the screen to the visible area and the page never scrolls as a whole. No new library. Check on iPhone (Safari and Chrome) and Android if one can be borrowed.
- [ ] T29. Auto-deploy from GitHub: images built in CI and pushed to ECR, deployed through OIDC + SSM (no stored AWS keys, no SSH), secrets in SSM Parameter Store, and a CloudWatch alarm with logs

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