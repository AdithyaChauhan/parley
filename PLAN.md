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

### Task 22: Spam limits, and "Parley keeps working when Redis is down" (teaching mode, friend style)
- **Branch:** `feature/limits`
- **Goal:**
  1. Stop abuse: too many messages, password guessing, and fishing for emails. A server answers "slow down" (429) instead of doing the work.
  2. Decide and build what happens when Redis is down. Chatting must keep working: only the live extras pause.
- **Mode:** teaching mode, friend style, questions at the end as "In my words" prompts. Claude Code runs the checks itself and shows the results.

**Example first (Claude Code shows this before any code):**
```
 Redis key  limit:send:<Ana>   (a sorted set of send times, like presence in D22)
   10:00:00.1, 10:00:00.4, ... 20 sends in the last 10 s
 21st send at 10:00:06 → server: 429 "Too many messages", Retry-After: 4
                         (the oldest of the 20 leaves the 10 s window at 10:00:10)
 Each send: drop times older than 10 s → count → if under 20, add this one. All in one Redis transaction.

 Redis down:
   Ana sends        → saved in PostgreSQL as usual (201). The live push is lost, and catch-up fixes it later (D21).
   Chat list        → works, online shows "last seen recently" (unknown)
   Live line ticket → 503 "Live updates unavailable", and the app keeps retrying with its backoff (D21)
   Limits           → let requests through, and log it (better a little spam than no chat at all)
```

**The limits (D24):**

| What | Limit | Counted per |
|---|---|---|
| Send a message | 20 per 10 seconds | user |
| Log in (wrong password) | 5 failures per 15 minutes | email |
| Log in (any attempt) | 30 per 15 minutes | IP address |
| Sign up | 5 per hour | IP address |
| Start a chat by email | 20 per minute | user |
| Get a live ticket | 10 per minute | user |

**Steps:**
1. **`app/limits/service.py`:** `hit(key, limit, window_seconds)` returns allowed, or "wait N seconds". It uses a sliding window in one Redis transaction, with a timer on the key so idle keys vanish. If Redis is down, it allows the request and logs a warning.
2. **Apply the limits** from the table above.
   - A 429 reply carries a `Retry-After` header.
   - A successful log-in clears that email's failure count.
   - Once an email is locked, even the right password gets 429 until the time passes.
   - The IP comes from `request.client.host`. Behind Nginx (T26) that becomes the proxy's IP, so the T26 brief must set uvicorn's `--proxy-headers` and trust only Nginx.
3. **Redis down, done properly:**
   - Chat list presence: `online: false`, `last_seen: null`.
   - Ticket: 503.
   - Publish: already never raises (D20).
   - The live listener keeps retrying (T21).
4. **App (fast mode):**
   - A send that gets 429 stays "waiting", is sent again after `Retry-After`, and keeps its order (outbox).
   - Log-in and sign-up 429 shows "Too many tries. Try again in N minutes."
   - The "+" box 429 shows "Slow down a moment."
   - Ticket 503 counts as "line down", so it just keeps backing off.
5. **Tests:**
   - The 21st send in 10 s gives 429 with `Retry-After`, and it works again after the window (expire the key for real, as T21 did).
   - The 6th wrong password locks that email, even with the right password, but not other emails.
   - A good log-in clears the count.
   - Sign-up's per-IP limit works.
   - **Redis down** (point the client at a dead port or make it raise): a send still gives 201 and the row is saved, the chat list gives 200 with `online: false`, a ticket gives 503, and limits let requests through.
- **Not in this task:** CAPTCHA, email verification, banning accounts.
- **Done when:**
  - Pasting and sending 25 quick messages: about 20 go at once, and the rest wait and then go, in order, with no doubles.
  - 6 wrong passwords show "Too many tries".
  - **Redis stopped** (`docker compose stop redis`): Ana can still send, and Ben sees it after a reload. The dots go grey with "Reconnecting...".
  - **Redis started again:** live updates come back by themselves, and catch-up fills the gap.
  - All tests pass, CI is green (run link in the report), and "In my words" is filled in by Adithya.

"In my words" prompts: how the sliding window counts the last 10 seconds; why limits let requests through when Redis is down but PostgreSQL doesn't get the same treatment; why a wrong-password limit is per email and also per IP.

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
- [ ] T22. Spam limits (also decide what happens when Redis is down: today the live line and chat list fail, like when PostgreSQL is down)

### Phase 6: RabbitMQ
- [ ] T23. Notification worker with retries and a failed-jobs queue
- [ ] T24. Browser push notifications (Web Push). Push text must not contain message text (see D12). Web Push needs HTTPS (localhost counts); check again at T26

### Phase 7: Run it like production
- [ ] T25. Dockerfiles and Docker Compose for every part
- [ ] T26. Nginx in front of several backend copies (run uvicorn with --proxy-headers trusting only Nginx, so rate limits see the real IP) (demo: stop one copy mid-chat and the apps reconnect to the other through Nginx, with nothing lost) (turn on `secure=True` for the refresh cookie once HTTPS is on)

### Phase 8: Measure it
- [ ] T26b. Deploy Parley live on one AWS EC2 server: Docker Compose + Nginx + HTTPS (a cheap domain or a free subdomain), refresh cookie `secure=True`. First: set an AWS budget alert (about $10), and check the old delivery-delay Fargate service in ap-southeast-1 is stopped.
- [ ] T27. Prometheus metrics and a Grafana dashboard
- [ ] T28. Load test with 1,000 fake users; write up the results with the laptop's specs (include 1,000 users connecting at once, to check the per-copy subscribe lock from D23)

### Phase 9: Kubernetes
- [ ] T29. Run Parley on local Kubernetes
- [ ] T30. Optional, only if ready before the AWS free plan ends (around mid-December 2026): short EKS run with Terraform, and record a demo. Tear it all down the same day with `terraform destroy` (the cluster costs money every hour)

### Phase 10: Show it
- [ ] T31. README with an architecture diagram, screenshots, a demo video and the load-test results, plus a short "How I built this" section (planned with Claude, coded with Claude Code; Adithya made the decisions, reviewed and tested every change; LEARNING.md shows what he learned)

### Later
- End-to-end encryption phase: 1:1 text, one device, safety numbers (see D12) (chat-list previews then move to the app, since the server can't read the text)
- v2: groups, images and voice notes, reactions, edit and delete, search
- Optional: move notifications into their own service