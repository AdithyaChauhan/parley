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

### Task 15: Real chats on the screen (fast mode)
- **Branch:** `feature/connect-chats`
- **Goal:** the chat screen uses real data from T14 instead of fake data. You can start a chat by email, see your real chats, send messages, and scroll up for older ones.
- **Mode:** frontend fast mode. Summaries in the friend style (WhatsApp examples, under 5 lines).

**What you'll see in the app when it's done:**
- The chat list shows your real chats, with last message, time and unread count.
- The "+" button asks for an email and starts a chat.
- Open a chat: the newest messages show, oldest at the top. Scroll up and older ones load.
- Type, then Send: your message appears at once with one grey tick, and stays after a reload.

**Steps:**
1. **Chat list:** load from `GET /api/chats`.
   - Show the time in your own time zone (server times are UTC): "11:15", "Yesterday", or a date.
   - No chats yet: show "Start your first chat" with the "+" button.
2. **New chat ("+" button):** a small box asking for an email, then `POST /api/chats/direct`.
   - Add the reply to the list (same shape as a list row) and open it.
   - Errors under the field:
     - 404: "No Parley account with that email."
     - 400: "That's you."
     - Backend down: "Can't reach Parley."
3. **Conversation:** load `GET /api/chats/{id}/messages`.
   - Flip it so the oldest is at the top.
   - When you scroll to the top, load more with `before=<smallest number on screen>`, and keep the scroll position steady.
   - Stop when `has_more` is false.
4. **Send:**
   - Make a fresh `crypto.randomUUID()` for each new message.
   - Show it right away with a small "sending" look, then swap in the server's copy (matched by `client_msg_id`) with one grey tick.
   - If it fails, show "Not sent, tap to retry". The retry uses the **same** `client_msg_id`, so it can never double.
5. **Side panel:** real chat name and member count. The file tiles stay fake (v2).
6. **Remove the old fake chats and messages** from the main screen. Keep the fake-data file only if something still needs it.

- **Known and fine for now:**
  - New messages from the other person show only when you reopen the chat or reload. Live updates come in T17.
  - The unread count doesn't clear when you open a chat yet. Read bookmarks come in T18.
- **Test with two people at once:** use a normal window for Ana and a private (incognito) window for Ben. They don't share cookies, so both stay logged in.
- **Done when:**
  - Ana starts a chat with Ben by email and sends 3 messages.
  - Ben reloads and sees them, then replies.
  - 40+ messages scroll up smoothly, with no doubles and no jumps.
  - A send with the backend stopped shows "Not sent", and the retry after starting it again sends exactly one copy.
  - The 15-minute check: leave the app open 15+ minutes, then open another chat without reloading. It just works.
  - `npm run build` and lint pass, the PR is green (copy the run link from https://github.com/AdithyaChauhan/parley/actions before merging), and Claude Code has written the LEARNING.md section.

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
- [ ] T15. Connect the chat list and conversation screens to real data (check: leave the app open 15+ minutes, then load chats without reloading, to test the 401 → refresh → retry path)

### Phase 4: Live chat (WebSocket)
- [ ] T16. WebSocket connection with a one-time ticket (explain the ticket idea on its own first)
- [ ] T17. New messages appear instantly; "got it" replies give two ticks
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
- [ ] T27. Prometheus metrics and a Grafana dashboard
- [ ] T28. Load test with 1,000 fake users; write up the results with the laptop's specs

### Phase 9: Kubernetes
- [ ] T29. Run Parley on local Kubernetes
- [ ] T30. Optional, only if ready before the AWS free plan ends (around mid-December 2026): short EKS run with Terraform, and record a demo

### Phase 10: Show it
- [ ] T31. README with an architecture diagram, screenshots, a demo video and the load-test results, plus a short "How I built this" section (planned with Claude, coded with Claude Code; Adithya made the decisions, reviewed and tested every change; LEARNING.md shows what he learned)

### Later
- End-to-end encryption phase: 1:1 text, one device, safety numbers (see D12) (chat-list previews then move to the app, since the server can't read the text)
- v2: groups, images and voice notes, reactions, edit and delete, search
- Optional: move notifications into their own service