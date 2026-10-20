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

### Task 12: Connect the sign-up and log-in screens to the real backend (fast mode for the screens)
- **Branch:** `feature/connect-auth`
- **Goal:** the screens from T7 talk to the real backend from T10. Signing up makes a real row in `users`. A page reload keeps you logged in. Log out really logs you out.
- **Mode:** frontend fast mode for the React parts. The one small backend change (step 1) gets a short explanation.

**Carry-over from T11 (do first):**
- Commit the T11 section of LEARNING.md that's already drafted. Adithya answers the 3 T11 questions and writes "In my words" for T11.
- The red-cross proof: break `test_health` on purpose, push, see the red cross on the PR, `git revert HEAD`, push, see green again. Put the run links in the report.

**How the pieces talk (D17):**
```
 Browser  ──>  Vite dev server (localhost:5173)
                 │  /api/...  is passed on (the "proxy") to
                 ▼
               FastAPI (127.0.0.1:8000)  /api/auth/signup, /login, /refresh, /logout, /me
 The browser thinks it's all ONE site, so the refresh cookie just works.
```

**Steps:**
1. **Backend (small):** move every route under `/api` (`/api/health`, `/api/health/db`, `/api/auth/...`), set the refresh cookie's path to `/api/auth`, and update the tests. CI must stay green.
2. **Vite proxy:** in `vite.config.ts`, send `/api` to `http://127.0.0.1:8000`.
3. **Pages with addresses (React Router, D7):** `/login`, `/signup`, and `/` (the chat screen). `/` sends you to `/login` if you're not logged in. `/login` and `/signup` send you to `/` if you are.
4. **`src/lib/api.ts`:** one small fetch helper.
   - It adds `Authorization: Bearer <token>` to every request.
   - On a 401 from a normal request, it refreshes once and retries.
   - Only one refresh runs at a time: other requests wait for it. If the refresh itself gets 401, it waits about 300 ms and tries once more, because another tab may have just rotated the cookie. Then it gives up and logs out.
5. **`src/features/auth/AuthProvider.tsx`:** keeps the user and the access token in memory only (never in localStorage, D16). On page load it calls refresh, then `/api/auth/me`. While that runs, show a simple loading screen.
6. **Wire the forms:** sign-up and log-in call the API.
   - Server errors show under the right field, in the T7 style:
     - 409 means "That email is already taken."
     - 401 means "Wrong email or password."
     - 422 shows the field problems.
     - If the backend is down: "Can't reach Parley. Try again."
   - Log out calls `/api/auth/logout`, then goes to `/login`.
7. **Chat screen:** the profile shows the real logged-in name (instead of the fake "Kiran Rao"). Chats and messages stay fake until T15.

- **New library (D7 updated):** react-router. Use its current version in "declarative" mode (`BrowserRouter`, `Routes`, `Route`), checked in its docs.
- **Not in this task:** real chats or messages (T13–T15), remember-me options, password reset.
- **Done when:**
  - Signing up in the browser adds a row in `users` (check in psql).
  - Reload keeps you logged in, and log out sends you to `/login`.
  - A reload after log out stays logged out.
  - Two tabs open for over 15 minutes, both still work.
  - A wrong password shows the right message, and a stopped backend shows "Can't reach Parley".
  - The PR shows a green tick, and Claude Code has written the LEARNING.md section.

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
- [ ] T12. Connect the sign-up and log-in screens to the real backend (only one refresh at a time per tab, other requests wait for it; if a refresh gets 401, wait a moment and retry once, since another tab may have just rotated the cookie; use a Vite proxy so the cookie works)

### Phase 3: Messages over HTTP
- [ ] T13. Chat tables (start the brief with the table map; add the new tables to the conftest TRUNCATE; route tests always use the `client` fixture): chats, chat members, messages (per-chat numbers, message IDs). The brief must explain how two messages sent at the same moment never get the same number (a lock or a counter column)
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
- [ ] T26. Nginx in front of several backend copies (turn on `secure=True` for the refresh cookie once HTTPS is on)

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