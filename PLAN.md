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

### Task 18: Read ticks (teal) and "typing..." (teaching mode, faster)
- **Branch:** `feature/read-typing`
- **Goal:**
  - When Ben actually looks at Ana's messages, her ✓✓ turns teal and his unread count clears for good.
  - While someone types, the other person sees "Ben is typing..."
- **Mode:** teaching mode, friend style, faster (questions at the end, as "In my words" prompts). Claude Code runs the backend checks itself and shows the results.
- **Testing two people:** a normal window for Ana plus a private (Incognito) window for Ben.

**Example first (Claude Code shows this before any code):**
```
 Ben's chat list loads           → app says "delivered 12"   (Ana sees grey ✓✓)
 Ben OPENS the chat, sees #12    → app says "read 12"         (Ana sees teal ✓✓, Ben's unread → 0)
 Ben types "ok"                  → app says "typing" (at most every 3 s)
                                   server passes it on, saves nothing
                                   Ana sees "Ben is typing..." for 5 s, or until Ben's message arrives
```
Rule of thumb: **delivered** means "it's on my device". **Read** means "it was on my screen in an open chat, with the window in front". The chat list never sends read.

**Steps:**
1. **Backend: `read`.**
   - The line accepts `{"type":"read","data":{"chat_id","seq"}}`.
   - `mark_read` works like `mark_delivered`: members only, forward-only, capped at `last_seq`. It **also lifts `delivered_up_to`** to at least the same number (read implies delivered).
   - If anything moved, push `receipt` with **both** bookmarks: `{chat_id, user_id, delivered_up_to, read_up_to}`.
2. **Backend: small fix from T17.** On send, also lift the sender's own `delivered_up_to` (today only their `read_up_to` moves).
3. **Backend: `typing`.**
   - The line accepts `{"type":"typing","data":{"chat_id"}}`.
   - The server checks the person is a member, then pushes `{"type":"typing","data":{chat_id, user_id}}` to the **other** members. Nothing is saved.
   - Ignore extra typing events from the same line within 1 second.
4. **Frontend (fast mode):**
   - **Sending `read`:** when a chat is open, the window is in front (visible and focused) and the newest message is on screen, send `read` with the highest number shown. Send again when new ones arrive while you watch. Set that chat's unread to 0.
   - **Ticks:** my #N shows teal ✓✓ when the other person's `read_up_to` ≥ N, grey ✓✓ when only `delivered_up_to` ≥ N, and ✓ otherwise.
   - **Sending `typing`:** while you type, send `typing` at most once every 3 seconds.
   - **Showing typing:** show "<name> is typing..." with the animated dots in the conversation, and "typing..." in the chat list row. Hide it 5 seconds after the last event, or as soon as that person's message arrives.
5. **Tests:**
   - `read` moves both bookmarks, and the receipt carries both.
   - `read` never goes backwards or past `last_seq`.
   - A non-member's `read` and `typing` are ignored.
   - `typing` reaches the other member but not the sender.
   - A second `typing` inside 1 second is dropped.
   - The sender's `delivered_up_to` moves on send.
- **Not in this task:** catching up after a dropped line (T19), online and last-seen (T20), turning read receipts off (v2).
- **Done when:**
  - Ana sends. With Ben's chat **closed**, it shows grey ✓✓. When Ben opens the chat, it turns teal ✓✓, and Ben's unread clears and stays cleared after a reload.
  - With Ben's window in the background, the message stays grey until he comes back.
  - "Ben is typing..." shows while he types and goes away after he stops or sends.
  - All tests pass, CI is green (run link in the report), and "In my words" is filled in **by Adithya, in his own words**.

"In my words" prompts: how the app decides a message is "read" and not just "delivered"; why typing is never saved in the database; what Ana's app checks to pick ✓, grey ✓✓ or teal ✓✓.

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