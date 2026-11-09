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

### v2 is built (T35-T38, Nov 8-9, 2026). Last step: Adithya's iPhone session
Use the live site, with Ana on the laptop (Chrome) and Ben on the iPhone (Safari). About 15 minutes.

**Groups**
1. Ana creates a group with Ben. It appears on the iPhone right away, the header shows the names, and names show above the bubbles.
2. Messages go both ways, and "Ana is typing..." shows on the iPhone.

**Files**
3. Ben sends a photo from the iPhone: progress shows, it appears on both sides, and tapping it opens it large.
4. Ben sends a PDF from Files: a card shows, and it downloads on the laptop.
5. Ben holds the mic, records about 5 s, and lets go: it plays on the laptop. A voice note from Ana plays on the iPhone.

**Reactions, edit, delete**
6. A long press on Ana's message opens the menu, with no text selection or iOS popup. Reacting with 👍 shows on the laptop.
7. A long press on Ben's own text, then Edit: the keyboard opens at once, and saving shows "edited" on both sides.
8. Delete a photo and a text for everyone: both become "This message was deleted" on both sides.
9. "Copy" in the menu pastes the right text (for example into Notes).
10. Scrolling the chat doesn't open the menu by accident.

**Search**
11. Search a word from the chat list: the result shows, and tapping it jumps to the message.
12. Log out on the iPhone and log back in: search starts empty.

**Finish**
13. Ana removes Ben from the group: the iPhone shows the chat read-only, with a note.
14. In Chrome on the iPhone, repeat 3, 5 and 6.

Anything that fails goes to Claude Code as a fix task (`fix/...`), with a screenshot.

**After that:** v2 is done. What's left is optional: T33 (the EKS run, only before Feb 2, 2027), the small items in "Later", or the bigger "Later" phases (end-to-end encryption, Status, calls).

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
- [x] Fix: Parley under load: a thread/connection deadlock, and the password-check cap (D34, PR #37)

### Phase 10: Kubernetes
- [x] T32. Run Parley on local Kubernetes (with liveness probes, so a stuck copy restarts by itself, D34, D35)
- [ ] T33. Optional, only if ready before the AWS free plan ends (Feb 2, 2027, or when the credits run out): short EKS run with Terraform, and record a demo. Tear it all down the same day with `terraform destroy` (the cluster costs money every hour). It can slot in between v2 tasks, any time before Feb 2. Set RabbitMQ's memory alarm there (D35)

### Phase 11: Show it
- [x] T34. README with an architecture diagram, screenshots, a demo video and the load-test results, plus a short "How I built this" section (planned with Claude, coded with Claude Code; Adithya made the decisions and reviewed the work; up to T31 he also tested every change himself, and from the load fix on (build mode) Claude Code ran the checks; LEARNING.md shows what he learned). First re-run load tests b and d with other apps closed, for clean numbers (the Nov 6 runs had Windows paging)

### Phase 12: v2 (Nov 7-9, 2026, one PR per task; iPhone session pending)
- [x] T35. Groups: one message fans out to many people (D37). Brings back the "..." menu ("New group") and the members view
- [x] T36. Files and voice notes: images, documents and voice notes in S3-style storage (D38). Brings back attach and file drop
- [x] T37. Reactions, edit and delete (D39). Brings back the emoji button (PR #43)
- [x] T38. Search, only on your own device (D12, D40)

### Later
- End-to-end encryption phase: 1:1 text, one device, safety numbers (see D12) (chat-list previews then move to the app, since the server can't read the text)
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
- Small: balance HTTP and live lines separately. `least_conn` counts WebSockets, so a 513/487 split sent most HTTP to one copy (D36). Options: a separate upstream for `/api/live`, or round robin for plain HTTP. Not measured.
- Small: stop a sender from replacing their own sent file during the 5-minute upload link (D38). For example, copy it to a final key when the message is saved, or refuse overwrites if Garage supports that.
- Small: a size limit or a word index for search's copy on the device (today a search reads every row, about 0.5 s at 20,000). Rethink the copy when end-to-end encryption comes, since it isn't encrypted on the device (D40).