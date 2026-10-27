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

### Task 27: Responsive layout fix (fast mode)
- **Branch:** `fix/responsive-layout`
- **Goal:** Parley looks right at every window size, from a 360 px phone to a wide desktop, before the live link goes out (T28). Recruiters will open it on their phones.
- **Mode:** frontend fast mode (CLAUDE.md). There are no backend changes.

**What's broken today (Adithya's screenshots):**
- At about 1100-1250 px, three columns don't fit. The chat column gets crushed, so text wraps one letter per line, the avatar overlaps the "Messages" tab, and the send button sits on top of the files panel.
- At phone size, the "Chat" and "Shared files" titles are back, even though D8 removed them.
- Real chats show fake file counts ("23 files, 9 links").

**Target layout (final, after trying it in the browser):**
```
 1280 px and up   icon rail | list | chat | side panel      (the panel folds to a thin strip: open button + avatar only)
 768-1279 px      icon rail | list | chat                   (tap the name → the side panel takes the chat's place, back arrow returns)
 under 768 px     one screen at a time: list → chat → files, no bottom bar, a back arrow only
```
**Added during the task:** hide every button that does nothing yet. That's the rail icons other than Chats, the "available" pill, the "..." menu, emoji and attach, file drop, and the "Messages" and "Participants" tabs. A 1:1 side panel shows "online" or "last seen" instead of "2 members" (D8). Choices made: no bottom bar on phones, the Chats icon right under the logo in the rail, the folded strip shows only the open button and avatar, "Reconnecting..." appears under the name only while the line is down, and `UploadView.tsx` is deleted (it comes back from Git in v2).

**Rules:**
- The chat column has a minimum width and never gets squeezed below it. When there's no room, the layout moves down one size row instead.
- Bubbles are at most about 75% of the chat width and wrap between words. Only very long words, like links, may break mid-word.
- Header parts (avatar, name, last seen) never overlap. A long name shortens with "...".
- Under 768 px, the phone back arrow goes chat → list and files → chat. The list screen has no back arrow.
- Every chat shows a "No files yet" empty state in the side panel. The fake file numbers and `fake.ts` are removed (D8).
- Keep the look from D8: same colors, spacing and font. This task only changes how things fit.

**Checks (Adithya, Chrome DevTools device toolbar):** 360, 390, 768, 1024, 1280 and 1440 px, plus slowly dragging the window from wide to narrow. At each size: no overlaps, no crushed chat, and sending and reading still work.
- **Not in this task:** dark mode, a real files feature (v2), and new screens.
- **Done when:** every check size looks right, lint and build are clean, CI is green, and Claude Code drafts the LEARNING.md section including "In my words" (fast mode).

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
- [ ] T27. Responsive layout fix, and hide buttons that do nothing yet (fast mode), before going live: four columns from 1280 px, the side panel in the chat's place at 768-1279 px, one screen at a time under 768 px (D8)

### Phase 8: Go live
- [ ] T28. Deploy Parley live on one AWS EC2 server: Docker Compose + Nginx + HTTPS (a cheap domain or a free subdomain), refresh cookie `secure=True`. AWS extras (D29), all in `deploy/aws/`: Terraform for the server, ECR for images, GitHub Actions deploy through OIDC (no stored AWS keys), secrets in SSM Parameter Store, and a CloudWatch alarm. The app itself never needs AWS. Notes for the brief: the browsers subscribe to push again on the new site, so re-check the VAPID subject; real IP (D27) holds only while Nginx is the only thing in front, since a cloud load balancer in front would change X-Forwarded-For handling. First: set an AWS budget alert (about $10), and check the old delivery-delay Fargate service in ap-southeast-1 is stopped.

### Phase 9: Measure it
- [ ] T29. Prometheus metrics and a Grafana dashboard
- [ ] T30. Load test with 1,000 fake users; write up the results with the laptop's specs (with least_conn, judge the spread of open live lines, not request counts) (include 1,000 users connecting at once, to check the per-copy subscribe lock from D23)

### Phase 10: Kubernetes
- [ ] T31. Run Parley on local Kubernetes
- [ ] T32. Optional, only if ready before the AWS free plan ends (around mid-December 2026): short EKS run with Terraform, and record a demo. Tear it all down the same day with `terraform destroy` (the cluster costs money every hour)

### Phase 11: Show it
- [ ] T33. README with an architecture diagram, screenshots, a demo video and the load-test results, plus a short "How I built this" section (planned with Claude, coded with Claude Code; Adithya made the decisions, reviewed and tested every change; LEARNING.md shows what he learned)

### Later
- End-to-end encryption phase: 1:1 text, one device, safety numbers (see D12) (chat-list previews then move to the app, since the server can't read the text)
- v2, in this order: groups (one message fans out to many people), images and documents (S3-style storage: MinIO in Docker Compose by default, AWS S3 when configured, D29), voice notes, reactions (these bring back the emoji button), edit and delete, search (only for your own messages on your device, D12). Groups bring back the "..." menu ("New group") and the group members view.
- Maybe later: Status (24-hour stories, which bring back the eye icon: a good topic for expiry and fan-out), voice and video calls (WebRTC, a big topic on its own, which bring back the calls icon).
- Not planned: Dashboard, Tasks and Stats (they came from the reference design, not from WhatsApp), the "available" pill, and contacts sync.
- Optional: move notifications into their own service