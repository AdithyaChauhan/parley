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
- Each task's "Done when" also needs the task's "In my words" in LEARNING.md filled in by Adithya. For frontend tasks (fast mode, see CLAUDE.md), Claude Code drafts it and Adithya just reviews it.

---

## You are here

### Fix: phone keyboard layout (frontend fast mode)
- **Branch:** `fix/phone-keyboard`
- **Why now:** Parley is live (T28), and the link goes on the resume next. On an iPhone, the keyboard broke the chat screen.
- **Mode:** frontend fast mode (CLAUDE.md). There are no backend changes. Adithya tests on a Windows laptop and an iPhone (no Android).

**What's broken (iPhone, T28 screenshots):**
1. With the keyboard open, the message box is sometimes hidden behind the keyboard, so you type blind.
2. When the box does show, the whole page has slid up, and the chat header (back arrow, name, online) is off screen.
3. After the keyboard closes, the page stays slid up: the header is half cut off, and the newest message is hidden behind the message box.
- **Cause:** `ChatScreen.tsx` uses `h-svh` (a fixed height), so iOS scrolls the whole page instead of shrinking the message list.

**Target (WhatsApp behaviour, D8):**
```
┌──────────────────────┐
│ ← Ana  online        │  header: always at the top
├──────────────────────┤
│ messages scroll here │  only this part scrolls
├──────────────────────┤
│ [Write message…] (>) │  message box: just above the keyboard (or at the bottom)
├──────────────────────┤
│      ⌨ keyboard      │
└──────────────────────┘
```

**Approach (1A, approved):**
- `h-dvh` instead of `h-svh` for the full-screen layouts.
- Viewport meta `interactive-widget=resizes-content` (Android Chrome, harmless elsewhere).
- A small `visualViewport` listener so iOS sizes the screen to the visible area. The page as a whole never scrolls (no body scroll on the chat screen), and only the message list scrolls (`min-h-0` + `overflow-y-auto`).
- The message box text is at least 16 px, because iOS zooms the page when you tap a smaller input.
- Respect the iPhone home-bar area at the bottom (`env(safe-area-inset-bottom)`) when the keyboard is closed.
- **Scrolling:** sending jumps to the newest message. A new incoming message keeps you at the bottom if you were already there. If you've scrolled up to read old messages, it doesn't yank you down.
- No new library. Desktop and tablet layouts from T27 must not change.

**Testing on the iPhone before merging:** run Vite on the laptop so the phone can reach it on the same Wi-Fi (Claude Code gives the exact steps, including any Windows firewall prompt). If that doesn't work, deploy the branch to the server temporarily with `deploy.sh web`, then switch the server back to `main` after merging.

- **Not in this task:** a "turn on notifications" hint, new features, Android-only tuning.
- **Done when:**
  - On the iPhone (Safari and Chrome), with the keyboard open: the header is visible, the box sits just above the keyboard, and you see what you type.
  - Scrolling up through old messages: the header and box stay put, and only the messages move.
  - Sending jumps to the newest message. Closing the keyboard leaves no shift, and the newest message is visible.
  - Tapping the box doesn't zoom the page, and nothing scrolls sideways.
  - Desktop spot check (DevTools 1440, 1024, 390): same as T27.
  - Lint and build are clean, and CI is green (run link in the report).
  - After merging, the server runs it: `deploy.sh web` on `main`, checked on the iPhone on the live site.
  - Claude Code drafts the LEARNING.md section, including "In my words" (fast mode).

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
- [ ] Fix (right after T28): phone keyboard layout (brief in "You are here")
- [ ] Before sharing the link: a fresh, empty database on the server (removes the test accounts), then sign up clean demo accounts
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
- Small: a hint near "Turn on notifications" (it lives only in the gear menu and is easy to confuse with the browser's own site toggle).