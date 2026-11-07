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

### T35. Groups (build mode)
- **Branch:** `feature/groups`
- **Goal:** group chats that work like WhatsApp's basic groups. They're built on what already exists: the same message numbers, bookmarks, live line and catch-up. The rules are in D37.

**Backend**
- Tables and columns for groups, roles and membership start/end, using expand-then-contract (D31). The migration must be safe on the live database, with existing direct chats untouched.
- Routes: create a group (name and members), add, remove, leave, rename, make admin, and list members. Every route checks membership and role on the server. Each change is saved together with its system message, in one transaction.
- Sends, history, catch-up and the chat list work for groups and respect membership: nothing from before you joined, and nothing after you left.
- Fan-out, receipts, typing and notifications follow D37.
- Tests:
  - a removed member can't read, send or get pushes
  - two admins changing members at the same moment
  - the last admin leaving
  - system messages keep the numbers gap-free
  - group ticks use the lowest bookmark

**App (D8)**
- The "..." menu comes back with "New group": a name, plus people picked from your direct chats or added by email.
- The group header shows the name and member names. Tapping it opens the side panel with the members. Admins can add, remove and make admin there, and everyone gets "Leave group".
- Messages from others show the sender's name above the bubble, in a steady color per person. System messages are small centered notes. The group avatar uses the name's initials.
- A member who left or was removed sees the chat read-only, with a note and no message box.
- Works at all three window sizes (D8). Screenshots of each go in the report.
- Update the README's "what works" list and its v2 line.

**Measure (T31's tools, D33's rules)**
- One 50-member group at 2 and 5 msg/s: end-to-end p50/p95 to every member, pushes per second, and CPU. Write it up in `docs/load-test.md`.

- **Done when:**
  - Everything above is built, and the new and old tests pass.
  - A real-browser check through localhost:8080 with three users passes: create, add, remove, leave, rename, and the ticks.
  - The measurement is in `docs/load-test.md`.
  - CI is green.
  - LEARNING.md has the section with a draft "In my words".
  - Adithya's iPhone check (a group with Ana and Ben on the live site) is batched with T36-T38's checks at the end.

---

## Next briefs (run in order after T35, no planning round in between)

How to run them: each task starts in a new Claude Code chat, from an up-to-date `main`, after the previous PR is merged. Step 0 of every task is to check that the last deploy is green and the live site shows the new version. Adithya brings a report to the planning chat only when Claude Code stops for a decision, or at the end of the batch. Claude Code collects suggested PLAN and DECISIONS text in its report, and the planner folds it all in at the end. iPhone checks for T35-T38 are batched into one session at the end.

### T36. Files and voice notes (build mode)
- **Branch:** `feature/files`
- **Goal:** send images, documents and voice notes in direct chats and groups, like WhatsApp. The rules are in D38.

**Storage (D38)**
- An S3-compatible store runs in Compose (dev, CI, and the live server's Compose) and in the kind setup. MinIO's free edition is out (D38), so pick Garage or SeaweedFS. Choose by measured memory on the 2 GB server and by the S3 features you need (presigned URLs). Pin the version (D27), and record the choice and the numbers.
- The app code talks plain S3 (one small client, settings from the environment, D29), so AWS S3 would work by changing settings only.
- On the live server the store runs in Compose with a volume on the server's disk. That's no AWS change and no extra cost. Set a memory limit, and measure the server's free memory after the deploy.

**How files travel**
- The browser uploads straight to storage with a short-lived presigned URL that the backend hands out after checking membership. Storage is reached through Nginx on the same site (for example `/storage/`), so there's no cross-site setup.
- The message is saved only after the upload finishes (D9). It carries the file's key, name, type, size and, for images, width and height plus a small preview that the browser makes. The server never opens the file (D12's spirit).
- Downloads use short-lived presigned URLs, given only to current members of the chat (D37's membership rules apply).
- Limits: 10 MB per file. Images (JPEG, PNG, WebP, GIF), documents (PDF, TXT, DOCX, XLSX, PPTX, ZIP) and voice notes. Checked on the server and in storage. D24-style upload limits per user.
- Files that were uploaded but never sent are removed after a day.

**App (D8)**
- The attach button and file drop come back. Images show inline with the preview first, then the full image. Tapping one opens it large. Documents show as a card with the name, type and size, plus a download button. The side panel's "No files yet" becomes a real list of the chat's files.
- Voice notes: hold the mic button to record (the browser's MediaRecorder; iPhone Safari records a different format, so test both). Up to 2 minutes, with a player in the bubble (play/pause, length).
- An upload shows progress and can be cancelled. A failed upload shows "Not sent" with retry, like a text.
- Works at all three window sizes, and on iPhone Safari (the batched check).

- **Done when:** sending and opening all three kinds works in a direct chat and a group (real browser, three users); a non-member can't get a file URL (test); the size and type limits hold (tests); the store's memory on the live server is measured after the deploy; CI is green; the README's lists are updated; LEARNING.md has the section with a draft "In my words".

### T37. Reactions, edit and delete (build mode)
- **Branch:** `feature/message-actions`
- **Goal:** react to a message, edit your own text, and delete your own messages for everyone. The rules are in D39.
- Each change is an event with its own number in the chat (`kind` = `reaction`, `edit` or `delete`, pointing at the target message). So catch-up by number brings it (D21), and live pushes carry it like any message. History pages return messages with the latest state already applied, so a new device doesn't replay events.
- Reactions: one per person per message, from 6 emojis (👍 ❤️ 😂 😮 😢 🙏). Tap again to remove. Counts show under the bubble. The emoji button comes back (D8).
- Edit: your own text messages, within 15 minutes. The bubble shows "edited".
- Delete for everyone: your own messages, within 1 hour. The server erases the text and the file (from storage too). Everyone sees "This message was deleted". "Delete for me" comes later.
- Unread and notifications count only real messages (text, files, voice). Events and group notes don't (this updates D20's unread rule, D39). The chat list's preview skips events.
- Works in direct chats and groups, at all three window sizes. On phones, a long press opens the actions. On desktop, hovering does.
- **Done when:** all three work live between two browsers and after a reconnect (catch-up); the time limits and "own messages only" hold (tests); unread counts ignore events (test); CI is green; LEARNING.md has the section with a draft "In my words".

### T38. Search on your device (build mode)
- **Branch:** `feature/search`
- **Goal:** search your messages without the server ever searching them (D12). The rules are in D40.
- The app keeps the messages it has seen in IndexedDB, per user, and clears them on log-out. Edits and deletes update the copy.
- Search across chats from the top of the chat list, and inside a chat from its header. Results show the chat, the sender and the matching text, with the match highlighted. Tapping one jumps to the message, loading older pages if needed.
- An honest note in the search box: it searches messages this device has loaded. An optional "Load all my history" button fetches older pages (D24-style pacing).
- Works at all three window sizes.
- **Done when:** search finds messages across chats and inside a chat, stays right after edits and deletes, is empty after log-out (tests or browser checks); no server route searches text; CI is green; the README's lists are updated; LEARNING.md has the section with a draft "In my words".

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

### Phase 12: v2 (from Nov 7, 2026; target Nov 10, one PR per task)
- [ ] T35. Groups: one message fans out to many people (D37). Brings back the "..." menu ("New group") and the members view
- [ ] T36. Files and voice notes: images, documents and voice notes in S3-style storage (D38). Brings back attach and file drop
- [ ] T37. Reactions, edit and delete (D39). Brings back the emoji button
- [ ] T38. Search, only on your own device (D12, D40)

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