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

### Task 17: Messages arrive instantly, and two ticks when delivered (teaching mode, faster)
- **Branch:** `feature/live-messages`
- **Goal:** Ana sends and Ben sees it at once, with no reload. Ana's message goes from one grey tick (saved) to two grey ticks (on Ben's device). Teal "read" ticks come in T18.
- **Mode:** teaching mode, friend style, faster (CLAUDE.md updated): no stops for questions between steps; the questions come at the end, as prompts for "In my words".

**Carry-over:** Adithya fills the two empty bullets in LEARNING.md Task 14 "In my words".

**Example first (Claude Code shows this before any code):**
```
 10:00:00  Ana presses Send  → POST /messages → saved as #12 (one grey tick ✓)
 10:00:00  Server → Ben's open line:   {"type":"message.new","data":{chat_id, message #12}}
 10:00:00  Ben's app shows #12, then → server: {"type":"delivered","data":{chat_id, "seq":12}}
 10:00:00  Server sets Ben's delivered_up_to = 12 in chat_members
           Server → Ana's open line:   {"type":"receipt","data":{chat_id, user_id: Ben, delivered_up_to: 12}}
 10:00:00  Ana's app: every message of hers up to #12 shows two grey ticks ✓✓

 If Ben's app is closed: #12 stays ✓ until Ben opens the app, loads the chat, and his app says "delivered 12".
```

**Steps:**
1. **Switchboard safety:** `send_to_user` sends to each of the user's lines separately. A line that fails is dropped, and the others still get the event.
2. **Push on send:** after the message is saved (the commit), push `message.new` to every member of the chat, including the sender's other tabs. Skip the push when the send was a repeat (200).
   - The send route runs in a worker thread, so hand the push to the async side safely (for example `anyio.from_thread.run`).
   - A push that fails never fails the send. The message is already saved (D9).
3. **"delivered" from the app:**
   - The live line now reads `{"type":"delivered","data":{"chat_id","seq"}}` from the app.
   - The server checks that the person is a member, then moves their `delivered_up_to` up to `seq`. It **only ever goes forward** (never down), and never past the chat's `last_seq`.
   - Database work from the async line goes through a worker thread (D15 is sync).
   - If the bookmark moved, push `receipt` to the other members.
4. **Bookmarks in the API:** the history reply (`GET .../messages`) gains a `members` list: `[{user_id, delivered_up_to, read_up_to}]`. That way the app can draw the right ticks after a reload too.
5. **Frontend (fast mode):**
   - **`message.new`:** if that chat is open, add the message (no doubles: match by id or `client_msg_id`). Otherwise update that row's preview and time, and add 1 to unread if it's not your own. Move the chat to the top.
   - **Telling the server:** after showing messages from a chat (live, or loaded by history or the chat list), send `delivered` with the highest number you have.
   - **`receipt`:** redraw ticks. My message #N shows ✓✓ when the other person's `delivered_up_to` is N or more.
   - **"Not sent" messages** stay in their chat when you switch chats and come back (keep them per chat, above the Conversation).
6. **Tests** (use `with TestClient(app) as client` so HTTP and live lines share one event loop):
   - Ben's line receives `message.new` when Ana sends.
   - Ben's `delivered` moves his bookmark and Ana's line gets `receipt`.
   - `delivered` never moves backwards and never past `last_seq`.
   - A non-member's `delivered` is ignored.
   - A dead line doesn't stop Ben's other tab getting the event.
   - A repeated send (200) pushes nothing.
- **Not in this task:** read ticks and typing (T18), catching up after a dropped line (T19), Redis (T20/T21).
- **Done when:**
  - In two windows, Ana sends and Ben sees it instantly. Ana's tick goes ✓ then ✓✓ within a second.
  - With Ben's window closed, Ana's message stays ✓. Ben opens the app, and Ana's turns ✓✓ without her reloading.
  - All tests pass, CI is green (run link in the report), and "In my words" is filled in.

"In my words" prompts: how a new message gets from Ana's send to Ben's screen; how Ana's tick knows Ben's device got it; why a bookmark only moves forward.

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
- [ ] T17. New messages appear instantly; "got it" replies give two ticks (also keep a "Not sent" message in the chat when you switch chats and come back)
- [ ] T18. Typing indicator and read ticks
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