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

### Task 3: Create the React app
- **Branch:** `feature/react-app`
- **Goal:** a working, empty React app in `frontend/` that already uses Parley's font and colors, ready for T4 to build the layout.
- **Tools (D7):** Vite, React, TypeScript, Tailwind CSS, shadcn/ui. Use the current official setup steps from each tool's own docs. Don't guess versions.
- **A note on generated files:** commands like `npm create vite` make many files at once. That's fine. Claude Code doesn't write those by hand. After each command, it explains every file the command made, one at a time, in plain words. Files Claude Code writes itself still go one per step.
- **Steps:**
  1. Check Node.js is installed (`node -v`, `npm -v`). If not, Claude Code tells Adithya how to install the LTS version, and stops until it works.
  2. Make the app in a `frontend/` folder with Vite's React + TypeScript template. Run it once (`npm run dev`) to see the default page.
  3. Add Tailwind CSS v4 with its Vite plugin, following the official Tailwind guide for Vite (no `tailwind.config.js`; v4 sets the theme in CSS).
  4. Add shadcn/ui with its CLI, following its official Vite guide (it sets up the `@/` import path and the theme file).
  5. Put Parley's look into the theme, the modern way: one CSS file holds every color from `docs/design/look.md` as a CSS variable, and shadcn's own slots point at them (for example `--primary` = teal `#00A389`, `--background` = page `#DCE0E8`). Add the Outfit font from Google Fonts and the corner sizes. Components then use names like `bg-primary`, never raw hex codes.
  6. Add one shadcn component only: Button. It turns teal by itself through `--primary`.
  7. Replace the default Vite page with a small test page: "Parley" in Outfit on the `#DCE0E8` page color, inside a white card with 28px corners, and one teal shadcn Button.
  8. Make sure `frontend/.gitignore` covers `node_modules` and `dist`.
- **Not in this task:** layout, chat list, messages, routing, any other library or shadcn component. Those come in T4 to T7.
- **Done when:** `npm run dev` shows the test page, the font is Outfit, the button is teal `#00A389`, `npm run build` works with no errors. Claude Code writes the LEARNING.md section (fast mode).

Ask Adithya one question at the end: "What does Vite do, in your own words?"

---

## All tasks

### Phase 0: Setup
- [x] T1. Repo and plan files
- [x] T2. The look: Parley's colors, fonts and logo, plus screen sketches using the reference layout (reference screenshots go in `docs/reference/`)

### Phase 1: Screens with fake data (React)
- [ ] T3. Create the React app (Vite + TypeScript) with Tailwind CSS and shadcn/ui, plus a `.gitignore` for `node_modules`. Do it in two steps: Vite + Tailwind first, shadcn/ui after that works
- [ ] T4. App layout: icon rail, chat list column, conversation area
- [ ] T5. Chat list with fake chats: search, last message, time, unread count
- [ ] T6. Conversation with fake messages: bubbles, ticks, typing indicator, message box
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