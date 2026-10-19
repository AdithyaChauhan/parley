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

### Task 10: Sign up and log in (teaching mode, short explanations)
- **Branch:** `feature/auth`
- **Goal:** real accounts. People can sign up, log in, stay logged in for 7 days, and log out. Tested from `/docs`. The screens connect in T12.
- **Mode:** teaching mode, with SHORT explanations (max ~6 lines per idea) and the Excel picture: PostgreSQL = the Excel file, a table = a sheet, SQLAlchemy = the translator, Alembic = the builder.

**Start with a 3-line recap (Claude Code says this first):**
- Password hash: like a fingerprint of the password. We store the fingerprint, never the password, and compare fingerprints at log-in.
- Refresh token: a 7-day visitor pass the browser keeps. We store only its fingerprint in `sessions`, so someone who steals the database can't use it to log in.
- Access token: a 15-minute wristband. Every request shows it, and the server checks it with no database lookup.

**How log-in works:**
```
 1. POST /auth/login (email, password)
 2.   find user in "users" sheet ──> compare password fingerprint
 3.   add a row to "sessions" (fingerprint of a new random refresh token, expires in 7 days)
 4. <── access token (15 min, in the JSON reply)
        + refresh token (7 days, in an httpOnly cookie the page's code can't read)

 Every API call:  "Authorization: Bearer <access token>"  ──> server checks it, no DB needed
 After 15 min:    POST /auth/refresh (cookie)  ──> new access token + a NEW refresh token (old one stops working)
 Log out:         POST /auth/logout  ──> session row marked revoked, cookie cleared
```

- **New packages (D16):** argon2-cffi (password hashing), PyJWT (access tokens), email-validator (pydantic's email check, for EmailStr). Pin exact versions.
- **New setting:** `JWT_SECRET` in `.env` and a placeholder in `.env.example`. Make a strong one with `python -c "import secrets; print(secrets.token_urlsafe(64))"`.
- **Files (all in `backend/app/auth/`):**
  1. `security.py`: hash and check passwords (argon2); make and read access tokens (PyJWT, 15 min, holds the user id and session id); make a random refresh token (`secrets.token_urlsafe`) and its SHA-256 fingerprint.
  2. `schemas.py`: the shapes of requests and replies (pydantic). Sign-up: name 2 to 50 characters, email, password at least 8. Never return `password_hash`.
  3. `deps.py`: `get_current_user` reads the Bearer token, checks it, loads the user. Wrong or expired token gives 401.
  4. `routes.py` (an APIRouter, plugged into main.py):
     - `POST /auth/signup`: trim and lowercase the email (the CHECK rule needs it), 409 if the email is taken, save the user, then log them in (same reply as log-in).
     - `POST /auth/login`: trim and lowercase the email. A wrong email or password both give the same 401 "Wrong email or password" (don't reveal which accounts exist).
     - `POST /auth/refresh`: read the cookie, find the session by fingerprint, check not revoked and not expired, then rotate (new refresh token, new fingerprint saved) and return a new access token.
     - `POST /auth/logout`: mark the session revoked, clear the cookie.
     - `GET /auth/me`: needs the access token, returns id, name and email.
  5. Cookie settings: `httponly=True`, `samesite="lax"`, `path="/auth"`, `secure` off for local http (turned on in production later).
- **Tests (no database needed yet):** `tests/test_security.py` for hashing, token make/read, expired token rejected, and email trim/lowercase. Route tests that need the database come in T11.
- **Not in this task:** connecting the screens (T12), rate limits (T22), email verification, password reset.
- **Done when:** in `/docs`: sign up, log in, `/auth/me` works with the token (Authorize button), refresh gives a new token, log out then refresh fails with 401. A new row appears in `sessions` (check in psql). `pytest` passes. Adithya fills in "In my words".

Questions for Adithya (short): why a hash for passwords, why the same 401 for wrong email and wrong password, why the access token is short and the refresh token long, why the refresh token goes in an httpOnly cookie.

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
- [ ] T10. Sign up and log in: hashed passwords, short and long passes (tokens)
- [ ] T11. GitHub Actions: run the tests on every pull request (CI has no `.env`, so set `DATABASE_URL` and `JWT_SECRET` there and start a Postgres service)
- [ ] T12. Connect the sign-up and log-in screens to the real backend

### Phase 3: Messages over HTTP
- [ ] T13. Chat tables (start the brief with the table map): chats, chat members, messages (per-chat numbers, message IDs). The brief must explain how two messages sent at the same moment never get the same number (a lock or a counter column)
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