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

### Task 4: The main screen with fake data (fast mode)
- **Branch:** `feature/main-screen`
- **Goal:** the full desktop main screen from `docs/reference/reference-1.webp`, working with fake data, plus the folded side panel (reference-3), the upload view (reference-2) and the phone layout. Follow `docs/design/look.md` and `docs/design/screens.md`.
- **Mode:** frontend fast mode (see CLAUDE.md). Claude Code builds, Adithya runs and looks.
- **What to build:**
  1. Fake data in one file: about 6 chats (1:1 and one group), each with 8-12 messages, made-up names (D8), times, unread counts and tick states (sent, delivered, read).
  2. App layout: the app fills the whole browser window (no outer page frame, no outer rounded corners; see D8), with four columns: icon rail, chat column, conversation, side panel. Profile areas are compact so the chat list and file list get the most room.
  3. Icon rail: a simple Parley logo (a teal speech bubble with "P", our own design), 6 icons (lucide-react), an active-icon tile with the teal bar, your avatar at the bottom.
  4. Chat column: no header on desktop (phones keep a "Chat" title); the profile is the top of the column, with the settings gear in its corner: (avatar, online dot, name, "available" pill), search box that filters the list, "Last chats" with + and menu icons, chat rows (avatar or initials, name, time, preview, unread pill). Clicking a row opens that chat. "typing..." shows on one fake chat.
  5. Conversation: title, Messages / Participants tabs (only Messages works for now), messages with avatar, "Name, time" label and bubble (sharp corner rule), ticks beside the time on my messages, "Mira is typing" with animated dots, message box with emoji, attach and teal send button. Typing a message and pressing Enter or Send adds it to the list with one grey tick (fake, no backend).
  6. Side panel: no header on desktop (phones keep "Shared files" and a back arrow); a small ">" in its top-right corner folds it. Group avatar, name, member count, the two stat tiles and the four file type rows. Folded, it becomes the thin icon strip (reference-3) with a "<" to open it again.
  7. Upload view: dragging a file over the conversation shows the dashed border and teal upload circle (reference-2). Dropping does nothing yet (v2).
  8. Phone (under 768px wide): one column at a time, with the back arrow, and the icon rail as a bottom bar.
- **Avatars:** initials on soft tinted circles (no photos, D8).
- **Code layout:** `src/components/` for shared pieces, `src/features/chat/` for chat screens, `src/data/fake.ts` for fake data. Only React state (`useState`), no new libraries beyond D7.
- **Done when:** the screen looks like reference-1 side by side (layout, colors, spacing, shapes), the folded panel looks like reference-3, the upload view like reference-2, the phone layout works in the browser's phone view (F12, then the phone icon), `npm run build` and `npm run lint` pass, and Claude Code has written the LEARNING.md section.

---

## All tasks

### Phase 0: Setup
- [x] T1. Repo and plan files
- [x] T2. The look: Parley's colors, fonts and logo, plus screen sketches using the reference layout (reference screenshots go in `docs/reference/`)

### Phase 1: Screens with fake data (React)
- [x] T3. Create the React app (Vite + TypeScript) with Tailwind CSS and shadcn/ui, plus a `.gitignore` for `node_modules`. Do it in two steps: Vite + Tailwind first, shadcn/ui after that works
- [ ] T4. The main screen with fake data: layout, chat list, conversation, side panel, upload view, phone (T4 to T6 merged)
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