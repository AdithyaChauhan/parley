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

### Task 19: Reconnect and catch up on missed messages (teaching for the ideas, fast mode for the screens)
- **Branch:** `feature/reconnect`
- **Goal:** Parley survives a bad connection. If the line drops (Wi-Fi off, laptop asleep, server restart), the app reconnects by itself, fetches anything it missed, and sends any "Not sent" messages in order, exactly once. This is the demo for interviews.
- **Mode:**
  - The three ideas below are taught in friend style: backoff, catch-up by number, and heartbeat. They're the system design part.
  - The screen parts are fast mode.
  - Questions come at the end, as "In my words" prompts.

**Step 0 (carry-over from T18):** the read-receipt gap.
- Send `receipt` to everyone in the chat, **including the reader's own other tabs**.
- In the app, a receipt about someone else updates ticks. A receipt about me sets that chat's unread to 0.
- Test: Ben has two tabs, reads in one, and the other tab gets the receipt.

**Example first (Claude Code shows this before any code):**
```
 10:00:00  Ben's Wi-Fi drops. His app has Ana's chat up to #20.
 10:00:05  Ana sends #21, #22, #23. The pushes to Ben fail (line is dead). Saved anyway (D9).
           Ben's app: no "pong" for 10 s → line is dead → try again in 1 s, 2 s, 4 s ... (max 30 s)
 10:00:40  Wi-Fi back. Ben's app gets a new ticket, reconnects, gets "hello".
           Catch-up:  GET /api/chats                              (new previews, unread, new chats)
                      GET /api/chats/{open chat}/messages?after=20  → #21, #22, #23 (oldest first)
           Ben's app says "delivered 23" (and "read 23" if he's looking) → Ana's ticks update.

 Ben's own sends while offline:  "hi", "you there?", "ok"  → shown as "waiting" in order
 10:00:40  back online → sent one at a time, in order, each with its SAME client_msg_id
           → no doubles even if one of them actually got through before the drop (D18)
```

**Steps:**
1. **Backend: `after=` for history.**
   - `GET /api/chats/{id}/messages?after=N` returns messages numbered above N, **oldest first**, with `limit` (at most 100), `has_more` and `members`.
   - `before` and `after` together give 422.
2. **Backend: heartbeat reply.** The line answers `{"type":"ping"}` with `{"type":"pong"}`.
3. **App: heartbeat.** While the line is open, send `ping` every 25 seconds. If no `pong` comes back within 10 seconds, treat the line as dead: close it and reconnect.
4. **App: reconnect with backoff.**
   - When the line drops, wait 1 s, 2 s, 4 s, 8 s ... up to 30 s, plus a little random extra so thousands of apps don't all retry at the same second.
   - Get a **new ticket** each time.
   - Try at once when the browser says it's back online, or when the tab comes back to the front.
   - Reset the wait after a good connection.
   - The dot is grey, with a small "Reconnecting..." note, while it's down.
   - Never reconnect after log-out.
5. **App: catch-up on every hello after a drop.**
   - Reload the chat list.
   - For the open chat, fetch `after=<highest number on screen>`, repeating while `has_more`.
   - Re-send `delivered` and `read`, as T17/T18 already do.
   - Closed chats load normally when opened.
6. **App: gap check while connected.** If a pushed message for the open chat is more than one ahead of the highest number on screen (I have #20, a push brings #23), fetch `after=20` to fill the gap.
7. **App: outbox.**
   - Sends that fail because you're offline wait in order and show "waiting".
   - When the line is back, send them **one at a time, in order**, each with its own original `client_msg_id`.
   - A send refused for a real reason (for example 422) shows "Not sent, tap to retry", as before.
8. **Tests (backend):**
   - `after=` returns oldest first with the right `has_more`, and `before` with `after` gives 422.
   - `ping` gets `pong`.
   - The two-tab read receipt (step 0).
- **Not in this task:** online status and last seen (T20), several backend copies (T21).
- **Done when:**
  - **Server restart:** with Ana and Ben chatting, stop and restart uvicorn. Both dots go grey, then green again without a reload, and anything sent meanwhile appears.
  - **Offline sends:** in Ana's DevTools → Network, set "Offline". Ana sends 5 messages, and they show "waiting". Set "No throttling". All 5 arrive at Ben, in order, exactly once (check in psql: 5 new rows).
  - **Missed messages:** Ben goes Offline, Ana sends 3, Ben goes back online. Ben's open chat shows them without a reload, and Ana's ticks update.
  - All tests pass, CI is green (run link in the report), and "In my words" is filled in by Adithya.

"In my words" prompts: how the app knows the line is dead; how catch-up finds exactly the messages you missed; why waiting messages can be re-sent without making doubles.

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
- [ ] T19. Reconnect and catch up on missed messages

### Phase 5: Redis
- [ ] T20. Online and last seen, with automatic expiry
- [ ] T21. Two backend copies; live messages cross between them (pub/sub)
- [ ] T22. Spam limits

### Phase 6: RabbitMQ
- [ ] T23. Notification worker with retries and a failed-jobs queue
- [ ] T24. Browser push notifications (Web Push). Push text must not contain message text (see D12). Web Push needs HTTPS (localhost counts); check again at T26

### Phase 7: Run it like production
- [ ] T25. Dockerfiles and Docker Compose for every part
- [ ] T26. Nginx in front of several backend copies (turn on `secure=True` for the refresh cookie once HTTPS is on)

### Phase 8: Measure it
- [ ] T26b. Deploy Parley live on one AWS EC2 server: Docker Compose + Nginx + HTTPS (a cheap domain or a free subdomain), refresh cookie `secure=True`. First: set an AWS budget alert (about $10), and check the old delivery-delay Fargate service in ap-southeast-1 is stopped.
- [ ] T27. Prometheus metrics and a Grafana dashboard
- [ ] T28. Load test with 1,000 fake users; write up the results with the laptop's specs

### Phase 9: Kubernetes
- [ ] T29. Run Parley on local Kubernetes
- [ ] T30. Optional, only if ready before the AWS free plan ends (around mid-December 2026): short EKS run with Terraform, and record a demo. Tear it all down the same day with `terraform destroy` (the cluster costs money every hour)

### Phase 10: Show it
- [ ] T31. README with an architecture diagram, screenshots, a demo video and the load-test results, plus a short "How I built this" section (planned with Claude, coded with Claude Code; Adithya made the decisions, reviewed and tested every change; LEARNING.md shows what he learned)

### Later
- End-to-end encryption phase: 1:1 text, one device, safety numbers (see D12) (chat-list previews then move to the app, since the server can't read the text)
- v2: groups, images and voice notes, reactions, edit and delete, search
- Optional: move notifications into their own service