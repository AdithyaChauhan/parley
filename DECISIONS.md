# Parley: Decisions

Every big choice and why. Both Claudes read this before suggesting anything.
To change a decision: discuss it in the planning chat, then add a new entry that replaces the old one. Never silently ignore an entry.

---

**D1. Name: Parley**
An old word for a talk between two sides.

**D2. A web app**
It runs in the browser (desktop first) and works on phone browsers. No mobile app.

**D3. How messages travel**
- Sending a message: a normal HTTP request (easy to test, clear success and error codes).
- Everything live (new messages, ticks, typing, online): one WebSocket connection.
- This is the same split Discord and Slack apps use.

**D4. Plain WebSockets, no Socket.IO**
We build reconnecting, "got it" replies and rooms ourselves, because that's what interviewers ask about.

**D5. One app first (a monolith)**
One backend split into clean folders by feature: auth, chats, messages, live.
Later we may move one piece (notifications) into its own service. Each new piece must connect to something that already works.

**D6. Backend: Python + FastAPI**
- Database: PostgreSQL, through SQLAlchemy.
- Database changes: Alembic migrations.
- Tests: pytest.
- Packages: pip with a virtual environment.

**D7. Frontend: React + TypeScript + Vite + Tailwind CSS + shadcn/ui**
Screens are built first with fake data. Then each backend feature plugs into a screen that already exists.

**D8. Look (updated)**
Parley matches the reference screenshots closely: layout, colors, spacing, shapes and font style.
Not copied: the logo, names and photos. Parley has its own logo, made-up names and its own avatars. The README credits the reference design.
Group chats, the side panel and uploads are built as screens first. They work for real in v2.

**D9. Message rules**
- Save to the database before sending anywhere.
- Each message carries an ID made by the sender's app, so a retried send is never saved twice.
- Each chat numbers its messages #1, #2, #3. Apps sort by this number, not by time.
- Ticks come from two bookmarks per chat member: "delivered up to #" and "read up to #".

**D10. Supporting tools (added in this order)**
- Redis: online status and passing messages between backend copies.
- RabbitMQ: notification jobs with retries.
- Docker Compose, then Nginx.
- Prometheus and Grafana.
- Kubernetes on the laptop.
Kafka is not used: RabbitMQ fits our jobs and is lighter.

**D11. AWS later**
Kubernetes runs on the laptop. A short EKS run happens only if ready before the AWS free plan ends (around mid-December 2026).

**D12. Encryption is a later phase**
- 1:1 text only, one device per user, Web Crypto (ECDH + AES-GCM), safety-number check.
- From day one, the server only passes message text along and never reads it: no message text in notifications, no server-side search.

**D13. Git workflow**
- `main` always works.
- One branch per task (`feature/`, `fix/`, `docs/`, `chore/`), merged by pull request.
- Adithya makes every commit and writes the message in his own words. Adding a "Co-Authored-By: Claude" line at the end is optional. Adithya decides each time.
- Private repo; goes public once live chat works.

**D14. Who does what**
- Adithya: final say. Nothing starts or merges without his OK.
- Planning chat (Claude on claude.ai): writes the plan, task briefs and decisions; teaches.
- Claude Code: writes project code, one file at a time. Adithya can write a file himself whenever he wants; he tells Claude Code first. Stops and reports if a brief clashes with the code or with this file.
- Only the planning chat changes PLAN.md and DECISIONS.md. Adithya copies the new versions into the repo.