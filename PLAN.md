# Parley: Project Plan

Parley is a real-time chat web app, like WhatsApp Web. It's a portfolio project to learn and show backend system design.

**How to use this file**
- One task at a time. Each task = one branch = one pull request.
- "You are here" shows the current task and its brief.
- After a pull request merges, Adithya tells the planning chat. The planner sends back a new PLAN.md (box ticked, "You are here" moved to the next task). Adithya replaces the file, and that goes in the next task's branch.
- Only the planner (chat Claude) writes task briefs. Claude Code never edits this file. It can only suggest changes.
- Adithya may write a file himself if he wants. He tells Claude Code, so it knows.
- Each task's "Done when" also needs the task's "In my words" in LEARNING.md filled in by Adithya. For frontend tasks (fast mode, see CLAUDE.md), Claude Code drafts it and Adithya just reviews it.

---

## You are here

### Task 7: Sign-up and log-in screens (fast mode, not connected yet)
- **Branch:** `feature/auth-screens`
- **Goal:** the sign-up and log-in screens from `docs/design/screens.md`, working with fake logic. T12 connects them to the real backend.
- **Mode:** frontend fast mode (see CLAUDE.md).
- **What to build:**
  1. Log-in screen: one white card (28px corners) centered on the `#DCE0E8` page. Parley logo at the top, a short title ("Welcome back"), email and password fields, a teal "Log in" button, and a small link "No account? Sign up".
  2. Sign-up screen: the same card with name, email and password fields, a teal "Sign up" button, and a link "Have an account? Log in".
  3. Fields: soft grey like the search box, a label above each field, and a show/hide eye on the password field.
  4. Checks in the browser before "sending": every field filled, email looks like an email, password at least 8 characters, name at least 2 characters. Errors show in red `#E5484D` text (12px) under the field. The button shows "Logging in..." / "Signing up..." for about 1 second.
  5. Fake result: a correct form opens the main chat screen. A "Log out" item somewhere simple (for example the settings gear) goes back to the log-in screen. Nothing is saved; a page reload starts at log-in.
  6. Switching screens: plain React state in `App.tsx` (log-in, sign-up, chat). No routing library yet (that's decided in T12).
  7. Phone: the card fills the width with a 16px gap on each side.
- **shadcn components allowed:** Input and Label (add them with the shadcn CLI). Nothing else new.
- **Code layout:** `src/features/auth/` for the two screens and their shared form pieces.
- **Done when:** both screens match `screens.md` and the look, the checks show the right errors, a correct form opens the chat screen, log out returns to log-in, the phone view works, `npm run build` and `npm run lint` pass, and Claude Code has written the LEARNING.md section.

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
- [ ] T7. Sign-up and log-in screens (not connected yet)

### Phase 2: Backend basics
- [ ] T8. FastAPI app with a health check, PostgreSQL in Docker Compose, a first tiny pytest test, and `.gitignore` entries for the Python venv and `.env`
- [ ] T9. First tables with SQLAlchemy and Alembic: users, sessions
- [ ] T10. Sign up and log in: hashed passwords, short and long passes (tokens)
- [ ] T11. GitHub Actions: run the tests on every pull request
- [ ] T12. Connect the sign-up and log-in screens to the real backend

### Phase 3: Messages over HTTP
- [ ] T13. Chat tables: chats, chat members, messages (per-chat numbers, message IDs). The brief must explain how two messages sent at the same moment never get the same number (a lock or a counter column)
- [ ] T14. Send a message and load history, 30 at a time
- [ ] T15. Connect the chat list and conversation screens to real data

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
- [ ] T26. Nginx in front of several backend copies

### Phase 8: Measure it
- [ ] T27. Prometheus metrics and a Grafana dashboard
- [ ] T28. Load test with 1,000 fake users; write up the results with the laptop's specs

### Phase 9: Kubernetes
- [ ] T29. Run Parley on local Kubernetes
- [ ] T30. Optional, only if ready before the AWS free plan ends (around mid-December 2026): short EKS run with Terraform, and record a demo

### Phase 10: Show it
- [ ] T31. README with an architecture diagram, screenshots, a demo video and the load-test results

### Later
- End-to-end encryption phase: 1:1 text, one device, safety numbers (see D12)
- v2: groups, images and voice notes, reactions, edit and delete, search
- Optional: move notifications into their own service