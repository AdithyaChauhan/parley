# Parley: Learning Notes

One section per task. Claude Code drafts the "What was built" part. Adithya writes "In my words" himself; a task isn't done until that part is filled in.

## Template (copy for each task)

### Task N: name
**What was built**
- `path/to/file`: what the file is for.
  - `function_name()`: what it does and why it exists.

**New ideas**
- Each new word or tool, in one plain sentence.

**In my words** (Adithya writes this)
- What this task does, as if explaining to an interviewer: This task added the routes that use the new tables: start a chat, send a message, and load history. POST /api/chats/direct takes an email and returns the direct chat — 201 if it made it, 200 if it already existed; if two clicks land at once, the UNIQUE direct_key refuses the second and returns the first. POST /api/chats/{id}/messages saves a message — 201 new, 200 for a resend with the same client_msg_id — and moves the sender's own read_up_to, so your own messages are never unread to you. GET /api/chats/{id}/messages loads history 30 at a time, newest first, paged by message number (before=N) rather than page number, asking for limit+1 to set has_more. Every route checks chat_members itself, because anyone can call the API by hand, and "not your chat" and "no such chat" both return 404 so nobody can fish for real chat ids.

- What I'd check first if it broke: A 401 means the access token expired after 15 minutes — log in again. A 404 on a chat I know exists means my chat_members row is missing or I'm using the wrong person's token. A resend giving 201 every time means add_message isn't returning created=False. Paging that looks wrong means checking before/limit and that has_more comes from asking for limit+1. Tests that pass alone but fail together mean conftest isn't emptying all five tables.

- What still confuses me: Paging is anchored to a message number (before=N), so new messages don't shift the pages. But I don't yet know what the client has to remember between pages — whether it keeps the oldest number it has seen and passes that as before, or something else.

---

### Task 1: Repo and plan files
**What was built**
- `PLAN.md`: every task in order, plus the brief for the current one.
- `DECISIONS.md`: every big choice and why, so nobody suggests something that clashes.
- `LEARNING.md`: this file.
- `CLAUDE.md`: rules Claude Code reads at the start of every session.

**New ideas**
- Branch: a separate copy of the code to work on one task without breaking `main`.
- Pull request: a request to merge a branch into `main`, where the changes get reviewed first.
- Plan mode: a Claude Code mode where it reads and proposes but can't change files.

**In my words**
- What this task does: 3 files claude.md(rules for claude code) decisions.md(every major change to avoid conflct) and plan.md(task in order + brief for curr task)
- Why two Claudes need shared files: so that each can bring up issues it faces which contradicts the plan so it can understand and make ammends.
- What still confuses me: None

---

### Task 2: The look
**What was built**
- `docs/reference/`: the 3 reference screenshots. Parley matches their layout, colors, spacing, shapes and font style, but not their logo, names or photos (D8).
- `docs/design/look.md`: Parley's style guide. Every color with its hex code and its job, the font (Outfit) and its sizes, tick colors, corners, spacing steps and shadows.
- `docs/design/screens.md`: the layout of every screen: main screen, side panel (open and folded), upload view, sign-up, log-in and phone.

**New ideas**
- Hex code: a six-digit code for a color, like `#00A389`. Screens use it so a color is exactly the same everywhere.
- Style guide: one file that fixes the colors, font and sizes before any screen is built, so every screen looks like part of the same app.
- Spacing steps: gaps come from a short list (4, 8, 12, 16, 24, 32px) instead of any number, which keeps the screens even.
- Sharp bubble corner: one corner of each bubble stays sharp and points to the sender, so you can see at a glance whose message it is.
- Wireframe (the text drawing in `screens.md`): a rough sketch of where things go on a screen, with no colors or detail.
- Responsive layout: the same app changes shape to fit the screen. On a phone, Parley shows one column at a time and the icon rail moves to the bottom.

**In my words** (Adithya writes this)
- What this task does, as if explaining to an interviewer: This task locks down Parley’s design system and layout rules before building. By mapping out exact color tokens, a strict 4px grid, and multi-column viewports in look.md and screens.md, we guarantee visual consistency and an ergonomic mobile experience across the entire app.
- What I'd check first if it broke:  would first check the global layout classes and the responsive breakpoint configurations. If elements look uneven, it usually means arbitrary pixel values were used instead of our approved spacing steps (16px or 24px), or the mobile viewpoint toggle is failing to collapse columns.
- What still confuses me: • Managing transition animations smoothly when toggling the right side panel between open and folded states, ensuring it doesn't cause sudden layout jumps or text clipping in the active conversation column.

---

### Task 3: Create the React app
**What was built**
- `frontend/`: the React app, made with Vite's React + TypeScript template (with ESLint).
  - `vite.config.ts`: turns on the React and Tailwind plugins, and makes `@/` mean `src/`.
  - `tsconfig.json`, `tsconfig.app.json`: TypeScript settings, plus the `@/` shortcut.
  - `eslint.config.js`: code checks. One rule is off for shadcn's generated files in `src/components/ui/`.
  - `components.json`: shadcn's settings (Radix, Nova style, Neutral, CSS variables).
  - `src/index.css`: Parley's whole theme. Every color from `look.md` as a `--parley-*` variable, shadcn's slots pointing at them, the Outfit font, corner sizes and text sizes.
  - `index.html`: loads Outfit from Google Fonts and sets the tab title to "Parley".
  - `src/components/ui/button.tsx`: shadcn's Button, made by `shadcn init`. Teal through `--primary`.
  - `src/lib/utils.ts`: the `cn` helper that joins class names and settles clashes.
  - `src/App.tsx`: the test page. "Parley" and a teal Button in a white 28px-corner card on the page color.
- `docs/design/look.md`: added the Border color, `#E0E0E0`.

**New ideas**
- Vite: runs the app while I work and builds it for the web.
- Tailwind CSS: style with short class names. Preflight clears the browser's default styles so we start clean.
- @/ import path: a shortcut meaning src/, so imports don't break when files move. TypeScript 6 dropped baseUrl, so we use paths only.
- dependencies vs devDependencies: what the app needs to run vs tools only for building and checking.
- shadcn/ui: not a package of components. Its CLI copies each component's code into my project, so I own it.
- Theme variables: colors live in one CSS file as variables. Components use names like `bg-primary`, so changing one variable restyles the whole app.
- `@theme`: Tailwind v4's way to add my own classes from CSS, for example `rounded-card` or `text-header`.
- Dark mode stays off: `dark:` classes only work under a `.dark` class, which Parley never adds.

**In my words** (draft by Claude Code, Adithya keeps or edits)
- What this task does, as if explaining to an interviewer: It sets up the React app with Vite, Tailwind and shadcn/ui, and puts Parley's colors, font and corners into one theme file so every screen uses the same names.
- What I'd check first if it broke: `src/index.css` (the theme and imports), then `vite.config.ts` (the plugins and the `@/` alias).
- What still confuses me: nothing

---

### Task 4: The main screen with fake data
**What was built**
- `frontend/src/data/fake.ts`: the fake data. Types for people, chats, messages, ticks and shared files, plus "me" (Kiran Rao), 12 people and 12 chats (one group) with 8-10 messages each, so the chat list fills the screen and scrolls. All names are made up (D8).
- `frontend/src/components/`: small pieces used in many places.
  - `Avatar.tsx`: a round avatar with initials on a soft tint, with an optional green online dot. `initials()` turns "Mira Patel" into "MP".
  - `Logo.tsx`: Parley's own logo, a teal speech bubble with a "P", drawn as an SVG.
  - `Ticks.tsx`: one grey tick (sent), two grey (delivered) or two teal (read).
- `frontend/src/features/chat/`: the chat screens.
  - `ChatScreen.tsx`: the whole main screen. It fills the whole browser window with no outer frame (D8), and the profile areas are compact so the lists get the most room. It holds all the state: the chats, which chat is open, whether the side panel is folded, and which column a phone shows. `selectChat()` opens a chat and clears its unread count. `sendMessage()` adds my message with one grey tick and an ID made in the browser (D9).
  - `IconRail.tsx`: the logo, 6 icons and my avatar. On a phone it becomes the bottom bar.
  - `ChatColumn.tsx`: my profile at the top (with the settings gear), the search box (it filters the list as you type) and the chat list. The "Chat" title only shows on a phone.
  - `ChatRow.tsx`: one chat in the list: avatar, name, time, last message (or "typing...") and the unread pill.
  - `Conversation.tsx`: title and tabs, the messages, "Mira is typing" with moving dots, and the message box. It also shows the upload view while a file is dragged over it.
  - `MessageBubble.tsx`: one message with its "Name, time" label. Their bubble has a sharp bottom-left corner next to the avatar, mine a sharp bottom-right one. `withMentions()` colors "@Name" teal.
  - `MessageBox.tsx`: the input with emoji, attach and the teal send button. Enter or Send calls `onSend`.
  - `UploadView.tsx`: the dashed border, teal upload circle and "Upload your file". Dropping does nothing yet (v2).
  - `SidePanel.tsx`: the chat's shared files: avatar, member count, two stat tiles and four file types. The small ">" in its top-right corner folds it into the thin icon strip. On a phone it has a back arrow and a "Shared files" title instead.
- `frontend/src/App.tsx`: now shows `ChatScreen` instead of the test page.
- `frontend/src/index.css`: added the darker icon color for each file tile, and the `animate-typing` animation for the typing dots.
- `frontend/vite.config.ts`: uses `import.meta.dirname` instead of `__dirname` for the `@/` path, which removes a Vite warning.
- `docs/design/look.md`: their bubble's sharp corner is now bottom-left (matching reference-1), each file tile lists its darker icon color, and the main screen fills the window (the 28px card is only for sign-up and log-in).
- `docs/design/screens.md`: no "Chat" or "Shared files" titles on desktop, the fold button in the side panel's corner, and the phone screens with their titles and back arrows.
- `frontend/package.json`: shadcn moved to `devDependencies`. It's only a tool for adding components, so `npm audit --omit=dev` (only what the app ships) now shows 0 problems. Plain `npm audit` still warns about `braces` until a fixed version comes out.

**New ideas**
- Component: a function that returns a piece of screen. Big screens are made from small components.
- Props: the inputs a component gets from its parent, like `chat` or `onSend`.
- State (`useState`): data a component remembers. When it changes, React draws the screen again.
- Lifting state up: the state lives in the top component (`ChatScreen`) and flows down as props, so every column shows the same open chat.
- Passing functions down: a child calls a function prop (like `onSelect`) to ask the parent to change its state.
- Derived data: the chat row's preview and time are worked out from the last message, not stored twice.
- Responsive classes: `md:` means "from 768px wide". Below that, only one column shows and the rail moves to the bottom.
- Drag-and-drop events: `dragenter`, `dragover`, `dragleave` and `drop`. The browser only allows a drop if `dragover` calls `preventDefault()`.

**In my words** (draft by Claude Code, Adithya keeps or edits)
- What this task does, as if explaining to an interviewer: It builds Parley's main chat screen with fake data. One top component holds the state, and the chat list, conversation and side panel just show it, so the backend can replace the fake data later without changing the screens.
- What I'd check first if it broke: `ChatScreen.tsx` (the state and what it passes down), then the column that looks wrong.
- What still confuses me: nothing

---

### Task 7: Sign-up and log-in screens
**What was built**
- `frontend/src/components/ui/input.tsx`, `label.tsx`: shadcn's Input and Label, added with `npx shadcn add input label`.
- `frontend/src/features/auth/`: the two screens and their shared pieces.
  - `validate.ts`: `checkName()`, `checkEmail()` and `checkPassword()`. Each returns an error message, or `""` when the value is fine. Name needs 2+ characters, email must look like `name@example.com`, password needs 8+ characters.
  - `AuthCard.tsx`: the white 28px card on the blue-grey page, with the logo, a title and the small "switch screen" link. On a phone it keeps a 16px gap on each side.
  - `FormField.tsx`: a label, a soft grey input and the red 12px error under it. A password field gets an eye button to show or hide it.
  - `LoginScreen.tsx`: "Welcome back" with email and password. `handleSubmit()` runs the checks; if all pass, the button shows "Logging in..." for 1 second and then the chat opens.
  - `SignupScreen.tsx`: "Create your account" with name, email and password. Same idea, with "Signing up...".
- `frontend/src/App.tsx`: holds which screen shows (`"login"`, `"signup"` or `"chat"`) in plain state. It starts at log-in, so a page reload always comes back to log-in.
- `frontend/src/features/chat/ChatScreen.tsx`, `ChatColumn.tsx`: the settings gear opens a small menu with "Log out", which goes back to the log-in screen.

**New ideas**
- Controlled input: React state holds what's in each field, and the input shows that state. So the code always knows the current value.
- Client-side checks: the browser checks the form before sending, so mistakes show at once. The backend must still check again, because anyone can skip the browser.
- `noValidate`: turns off the browser's own pop-up checks, so only our red messages show.
- `preventDefault()`: stops a form from reloading the page when it's sent.
- `aria-invalid` and `aria-describedby`: tell screen readers that a field has an error and where the error text is.
- Screen switching with state: one value in `App.tsx` picks the screen. A routing library (real URLs like `/login`) is decided in T12.
- `cn()` merging: it removes clashing classes. It reads a custom class like `text-body` as a color, so we write the size as `text-[length:var(--text-body)]`.

**In my words** (draft by Claude Code, Adithya keeps or edits)
- What this task does, as if explaining to an interviewer: It adds log-in and sign-up screens that check the form in the browser and then pretend to send it. One state value in App picks which screen shows, so T12 only has to swap the fake wait for a real backend call.
- What I'd check first if it broke: `validate.ts` for wrong errors, then the `screen` state in `App.tsx` if the wrong screen shows.
- What still confuses me: nothing

---

### Task 8: FastAPI app, health check, PostgreSQL in Docker Compose
**What was built**
- `.gitignore` (root): keeps the venv, Python and pytest caches, and `.env` out of Git. Written first, so nothing slips in before it exists.
- `backend/requirements.txt`: the four backend packages, pinned with `==` so every install is the same: fastapi, uvicorn, pytest and httpx2. httpx2 replaced httpx because newer Starlette (which FastAPI is built on) marks httpx as deprecated for its test client (approved by the planner).
- `backend/app/__init__.py`: empty. Marks `app/` as a Python package so it can be imported.
- `backend/app/main.py`: creates the FastAPI app (titled "Parley").
  - `health()`: the `GET /health` route. Returns `{"status": "ok"}` so tools can ask "are you alive?" (Docker, Nginx and Kubernetes use this later).
- `backend/pytest.ini`: tells pytest to find code in `backend/` (`pythonpath = .`) and tests only in `tests/`.
- `backend/tests/test_health.py`: the first test.
  - `test_health_returns_ok()`: calls `/health` through FastAPI's TestClient and checks the status is 200 and the body is `{"status": "ok"}`.
- `docker-compose.yml` (root): one service, `db`, running the official `postgres:17` image. Its settings come from `.env`, port 5432 is open to the laptop, a named volume (`db_data`) keeps the data, and a `pg_isready` healthcheck marks it healthy.
- `.env.example` (root, committed): the three database settings with placeholder values. The real `.env` is copied from it and never committed.

**New ideas**
- Virtual environment (venv): a private copy of Python inside the project, so its packages never clash with other projects. It can always be rebuilt from `requirements.txt`, so it isn't committed.
- Pinning: `fastapi==0.143.5` means exactly this version, so nothing changes by surprise.
- Route: a rule on the server that says "this method + this path → run this function", like `GET /health → health()`.
- Decorator: a line starting with `@` above a function. `@app.get(...)` adds the function to FastAPI's list of routes when the app starts.
- uvicorn: the server. It listens on a port and hands each request to FastAPI, which finds the route, runs it and turns the result into JSON.
- JSON: the text format browsers and apps use to swap data.
- Status code: a number sent with every answer. 200 means OK.
- TestClient: a fake browser that calls the app in memory. No server or port needed, so tests are fast and run anywhere.
- `assert`: "this must be true, or the test fails".
- Deprecated: still works, but will be removed in a future version.
- Image vs container: an image is a read-only package (a tiny Linux plus Postgres). A container is a running, isolated copy of an image.
- Docker Compose: reads `docker-compose.yml` and starts the containers it describes with one command.
- Port mapping: `"5432:5432"` means laptop port → container port. It's the door into the sealed container.
- Named volume: storage Docker keeps outside the container, so the data survives restarts and even deleting the container.
- Healthcheck: Docker runs `pg_isready` every 5 seconds. "Running" isn't the same as "ready", so this tells the two apart.
- `.env` vs `.env.example`: real secrets for one machine (git-ignored) vs a committed list of which settings exist. A committed secret stays in Git history forever, so the only safe fix is never committing it.
- Port clash: two programs on the same port. Another project's container was on port 8000 and answered `/health` too. The `/docs` title showed which app was really answering.

**In my words** (Adithya writes this)
- What this task does, as if explaining to an interviewer: we have built fastapi for backend server and integrated local postgresql database running in isolated docker container. We automated test using pytest and verified /health
- What I'd check first if it broke: I'd check /docs in 8000 port. verify .env parameters if they match with .env.example and run docker compose ps to see containers health
- What still confuses me: Nothing so far

---

### Task 9: First tables with SQLAlchemy and Alembic: users, sessions
**What was built**
- `backend/requirements.txt`: four new pinned packages: sqlalchemy (the ORM), psycopg[binary] (the PostgreSQL driver), alembic (migrations) and pydantic-settings (reads `.env`).
- `.env.example`: a new `DATABASE_URL` line, the app's full address for the database (`postgresql+psycopg://user:password@localhost:5432/database`).
- `backend/app/config.py`: the one place the backend reads its settings from.
  - `Settings`: lists the settings the app needs (just `database_url` for now) and fills them from the root `.env`. It stops at startup with a clear error if one is missing. `extra="ignore"` skips the `POSTGRES_*` lines, which are only for Docker.
  - `settings`: the one shared copy other files import.
- `backend/app/db.py`: how the backend talks to PostgreSQL.
  - `engine`: the link to the database. Keeps a pool of open connections to reuse. `pool_pre_ping` checks a saved connection still works before using it. `connect_timeout` gives up on a new connection after 5 seconds.
  - `SessionLocal`: makes sessions (one conversation with the database each).
  - `Base`: parent class for all models. Every model is recorded in `Base.metadata`, which Alembic reads.
  - `get_db()`: a FastAPI dependency. Opens one session per request and always closes it afterwards.
- `backend/app/auth/__init__.py`: empty. Marks `auth/` as a package (the auth feature folder, D5).
- `backend/app/auth/models.py`: the first two tables, as Python classes.
  - `User` (table `users`): `id` (UUID), `email` (unique, with a CHECK rule that it is lowercase), `name`, `password_hash`, `created_at`.
  - `UserSession` (table `sessions`): one logged-in device. `id` (UUID), `user_id` (points to `users.id`, deleted with the user, indexed), `refresh_token_hash` (unique), `created_at`, `expires_at`, `revoked_at` (empty until logout). Named `UserSession` so it isn't confused with SQLAlchemy's `Session`.
- `backend/alembic.ini`: Alembic's settings, made by `alembic init migrations`. The `sqlalchemy.url` line was removed so no password is ever in this file.
- `backend/migrations/env.py`: the script Alembic runs each time. Changed to load our models, use `Base.metadata` as the list of tables we want, and use the app's own `engine` and `DATABASE_URL`.
- `backend/migrations/script.py.mako` and `README`: made by `alembic init`. The template for new migration files, unchanged.
- `backend/migrations/versions/8d01e14c7065_create_users_and_sessions.py`: the first migration, made by `alembic revision --autogenerate`.
  - `upgrade()`: creates `users`, `sessions` and the `ix_sessions_user_id` index.
  - `downgrade()`: removes them again, in reverse order.
- `backend/app/main.py`: new route.
  - `health_db()`: `GET /health/db`. Runs `select 1` through `get_db`. Returns `{"database": "ok"}`, or status 503 with `{"database": "unavailable"}` if the database can't be reached.

**New ideas**
- The picture: PostgreSQL is an Excel file, a table is a sheet, SQLAlchemy is the translator from Python classes to sheets, Alembic is the builder that creates and changes the sheets.
- ORM (Object-Relational Mapper): maps tables to classes, rows to objects and columns to attributes, so we work with Python objects and it writes the SQL for us. Raw SQL is still allowed (`select 1`).
- Driver (psycopg): the piece that actually speaks PostgreSQL's network language. The ORM sits on top of it.
- Engine and connection pool: the engine is the link to the database. The pool keeps a few connections open to reuse, because opening a new one each time is slow.
- Session (SQLAlchemy): one conversation with the database. Changes are collected, then `commit()` saves them all together, or none.
- Dependency (FastAPI `Depends`): something FastAPI prepares before a route runs, like opening a session, and cleans up afterwards.
- `yield`: hands a value to the caller and pauses until the caller is done, then carries on (here: closes the session).
- Primary key: the one column that names each row (`id`).
- UUID: a long random id any program can make on its own without clashing. It can't be guessed the way 1, 2, 3 can.
- Foreign key: a column that points at a row in another table. `ON DELETE CASCADE` deletes the linked rows too.
- Unique constraint: no two rows can share this value.
- CHECK constraint: a rule the database checks on every row (here: email must be lowercase).
- Index: like the index at the back of a book. Finds rows fast without reading the whole table. Unique columns get one for free; foreign keys don't.
- Hash: a one-way fingerprint. Easy to make from a value, impossible to turn back. We store only hashes of passwords and refresh tokens, so a leaked database can't be used to log in.
- Migration: a saved list of table changes, kept in Git. Every copy of the database runs the same lists in the same order, and existing rows are kept.
- Autogenerate: Alembic compares our models with the real database and writes the difference as a migration. A person still reads it before running it.
- `alembic_version`: Alembic's own one-row table that remembers which migration the database is on.
- `upgrade head` / `downgrade`: run all migrations not yet done / undo one.
- psql: PostgreSQL's command-line tool. `\dt` lists tables, `\d users` shows one table's columns, `\q` quits.
- Status 503: "service unavailable". The server is up, but something it needs (the database) is not.
- Timeout: a limit on how long to wait. Without `connect_timeout`, a new connection to a stopped database waited forever on this laptop.
- Port clash (again): a Windows-installed PostgreSQL service (`postgresql-x64-17`) was also on port 5432 and answered instead of Docker's, giving "password authentication failed". Fixed by stopping it and setting it to Manual.

**In my words** (Adithya writes this)
- What this task does, as if explaining to an interviewer: The app can now open the database (the Excel file) through SQLAlchemy (the translator). Alembic (the builder) created the users and sessions sheets from a saved migration, and /health/db checks the app can reach the database
- What I'd check first if it broke: docker compose ps to see if db is running, /health/db, and whether something else is on port 5432
- What still confuses me: i dont know how many more tables, why and how will they be connected.

---

### Task 10: Sign up and log in
**What was built**
- `backend/requirements.txt`: three new pinned packages: argon2-cffi (password hashing), PyJWT (access tokens) and email-validator (pydantic's email check, for `EmailStr`).
- `.env.example`: a new `JWT_SECRET` placeholder and the command that makes a strong one. The real secret is only in `.env`.
- `backend/app/config.py`: new required setting `jwt_secret`. The app won't start without it.
- `backend/app/auth/security.py`: the toolbox. Nothing in it touches the database.
  - `normalize_email()`: trims spaces and lowercases.
  - `hash_password()` / `verify_password()`: argon2 fingerprint of a password, and the check at log-in. A wrong password returns `False` instead of crashing.
  - `create_access_token()`: a JWT holding the user id (`sub`), session id (`sid`), and when it was made and expires (`iat`, `exp`, 15 minutes), sealed with `JWT_SECRET`.
  - `decode_access_token()`: checks the seal and expiry and returns the contents. Only accepts our one algorithm (HS256) and requires `sub`, `sid` and `exp`.
  - `new_refresh_token()` / `hash_refresh_token()`: a random 7-day token and its SHA-256 fingerprint.
- `backend/tests/test_security.py`: 7 tests, no database. Right and wrong password, different hash each time, token round trip, expired token rejected, token with another secret rejected, stable refresh fingerprint, email trim/lowercase.
- `backend/app/auth/schemas.py`: shapes of requests and replies.
  - `Email`: trims and lowercases first, then checks it's a real email address. (Done here, not in the routes, because email-validator rejects leading spaces.)
  - `SignupRequest`: name 2 to 50 characters (trimmed), email, password at least 8. `LoginRequest`: email and password, no length rule.
  - `TokenOut`: `access_token` and `token_type: "bearer"`. `UserOut`: only `id`, `name`, `email`, so `password_hash` can never be sent.
- `backend/app/auth/deps.py`: `get_current_user`, the bouncer. Reads `Authorization: Bearer <token>`, checks it, loads the user. Missing, fake, changed or expired token, or a deleted user: 401. `HTTPBearer` adds the Authorize button to `/docs`.
- `backend/app/auth/routes.py`: the `/auth` router.
  - `_start_session()`: adds a `sessions` row with the refresh token's fingerprint, sets the cookie, returns an access token. Used by sign-up and log-in.
  - `_set_refresh_cookie()`: `httponly`, `samesite="lax"`, `path="/auth"`, `secure` off for local http, lasts 7 days.
  - `POST /auth/signup`: saves the user. If the UNIQUE rule on email refuses the row: 409. Then logs them in (201).
  - `POST /auth/login`: same 401 "Wrong email or password" for an unknown email and a wrong password. An unknown email is still checked against a dummy hash so both take the same time.
  - `POST /auth/refresh`: finds the session by fingerprint, checks not revoked and not expired, then rotates: new token, new fingerprint and a new 7-day expiry in the same row.
  - `POST /auth/logout`: marks the session revoked and clears the cookie (204).
  - `GET /auth/me`: needs the access token. Returns id, name, email.
- `backend/app/main.py`: plugs in the auth router.

**New ideas**
- Password hash (argon2): a slow, salted fingerprint. A thief who steals the `users` sheet can still guess passwords, but each guess is slow and only tests one user.
- Salt: random letters mixed into each password before hashing, so the same password gives a different fingerprint each time.
- SHA-256 for refresh tokens: fast and always the same for the same input. Fine because the token is already random and unguessable, and needed because we look up the row by fingerprint.
- JWT (access token): a short note ("user X, session Y, valid until 10:15") plus a seal made with the server's secret. Changing one letter breaks the seal. Checked without the database.
- Access token vs refresh token: a 15-minute wristband shown on every request vs a 7-day visitor pass used only to get new wristbands.
- Trade-off: the bouncer doesn't look in `sessions`, so after log-out an old access token still works until it expires. That's why it's short.
- Rotation: each refresh replaces the refresh token, so a copied old one stops working.
- httpOnly cookie: the browser stores it and sends it by itself, but the page's JavaScript can't read it, so injected scripts can't steal the refresh token. `path="/auth"` means it only goes to `/auth/...` routes.
- Bearer header: `Authorization: Bearer <token>`, the standard way to send an access token.
- Dependency as a bouncer: `Depends(get_current_user)` runs before a route; if it raises 401, the route never runs.
- Same error for wrong email and wrong password: different messages would let an attacker find which emails have accounts, then focus on those. Same for timing, hence the dummy hash.
- Status codes: 201 created, 204 done with no reply body, 401 not logged in, 409 conflict (email taken), 422 the request's shape is wrong (bad JSON, short password).
- The database as the last guard: the UNIQUE rule on email stops duplicates even if two sign-ups arrive at the same moment.

**In my words** (Adithya writes this)
- What this task does, as if explaining to an interviewer: Adds accounts: sign up, log in, stay logged in, log out.

Passwords are hashed with argon2; only the hash is stored.

Log-in gives two tokens: a 15-minute JWT access token (checked by its seal, no database) and a 7-day refresh token in an httpOnly cookie (checked against the sessions table, so it can be cancelled).

Refresh swaps a valid refresh token for a new access token and rotates the stored fingerprint, so the old one dies.

Log-out stamps revoked_at, so the next refresh is 401.

Duplicate emails are stopped by the database's UNIQUE rule → 409.

Unknown email still runs a dummy argon2 check, so both failures take the same time and return the same 401.
- What I'd check first if it broke: /health/db — it only runs select 1, so a failure proves the problem is below my code, not in it. One click eliminates the whole database layer.

psql → \dt — code can be perfect while the tables were never created (fresh clone, CI). Missing tables → alembic upgrade head, done. "Relation does not exist" is a different bug from "wrong password."

Is JWT_SECRET unchanged? — it explains one specific symptom nothing else does: a token issued seconds ago being rejected. Nothing wrong with the token; the stamp changed.

Is the cookie arriving? — refresh reads the cookie, not the body. A valid sessions row plus a 401 means the server never got what it was looking for, so it's transport, not data.

select id, user_id, expires_at, revoked_at from sessions; — 401 is deliberately vague; only the table tells you which case it is. No row = never written. revoked_at set = you logged out. Row valid but 401 = the lookup is the bug, not the row.

Server log, then pytest last — the log shows what the code actually saw. And my 8 tests don't touch the database, so they'd pass while the routes are broken. Run them after you know it's in the routes, to confirm the machines are fine.
- What still confuses me: The rotation race: two tabs refreshing at once both send the same old cookie, the first rotates it, the second gets 401. I get why, but not yet what the frontend should do about it.

---

### Task 11: GitHub Actions runs the tests on every pull request
**What was built**
- `.env.example`: a new `TEST_DATABASE_URL` placeholder (same as `DATABASE_URL`, but the database name ends in `_test`) and the one command that creates the test database.
- `backend/tests/conftest.py`: setup shared by all tests. pytest loads it before any test file.
  - `_TestDatabase`: reads `TEST_DATABASE_URL` from the shell (CI) or `.env` (laptop). It doesn't import `app.config`, because that would build the app's settings with the real `DATABASE_URL` first.
  - Safety check: stops the whole run if the database name doesn't end in `_test`, because the tests empty tables.
  - Sets `DATABASE_URL` to the test database before the app is imported. A real environment variable wins over `.env`, so the whole app (and Alembic) uses the test database.
  - `test_database` fixture: runs `alembic upgrade head` once per test run, so the test sheets are built by the same migrations as the real ones.
  - `client` fixture: a fresh test browser for each test, then `TRUNCATE users, sessions` so the next test starts clean. Only tests that ask for `client` need the database; `test_health` and `test_security` still run without it.
- `backend/tests/test_auth_routes.py`: 6 tests through the real routes.
  - Sign-up gives 201 and a refresh cookie; the same email again gives 409.
  - Log-in with the right password gives 200.
  - Wrong password and unknown email both give 401 with the exact same reply.
  - `/auth/me` works with the token (and never shows `password_hash`), and gives 401 without it.
  - Refresh works with the cookie, and the cookie changes (rotation).
  - After log-out, refresh gives 401. The test puts the old cookie back by hand first, because log-out deletes it from the test browser. Without that, the 401 would only prove the cookie was gone, not that the session was closed.
- `.github/workflows/ci.yml`: runs on every pull request to `main` and every push to `main`.
  - `backend` job: a Postgres 17 service container with a health check, Python 3.13, `pip install` (cached), fake test-only `DATABASE_URL` / `TEST_DATABASE_URL` / `JWT_SECRET`, then `alembic upgrade head` and `pytest`.
  - `frontend` job: Node 24, `npm ci` (cached), `npm run lint`, `npm run build`.
  - Uses `actions/checkout@v7`, `actions/setup-python@v7`, `actions/setup-node@v7` (current majors, checked in their docs). `permissions: contents: read`: the workflow can only read the code.

**New ideas**
- CI (continuous integration): a robot runs the checks on every push and pull request, so a broken change shows a red cross before it reaches `main`, not after.
- GitHub Actions: GitHub's CI. It reads every `.yml` file in `.github/workflows/`.
- Workflow, job, step: the workflow is the whole recipe; a job is one set of steps on its own computer (backend and frontend run side by side); a step is one command or one ready-made action.
- Runner: a fresh, empty Linux computer GitHub lends for one job and then throws away. It has no `.env`, no packages and no database until the steps add them.
- Service container: a helper program (here Postgres) started next to the job and deleted with it. The health check makes the steps wait until it accepts connections.
- Action (`uses:`): a ready-made step someone else wrote, for example "check out the code" or "install Python". The `@v7` pins the major version.
- Dependency cache: CI saves the downloaded pip and npm packages and reuses them while `requirements.txt` / `package-lock.json` stay the same, so runs are faster.
- `npm ci`: installs exactly what `package-lock.json` says, from scratch. Stricter than `npm install`, which is what CI wants.
- Test database: tests create and delete rows freely, so they get their own database. Your own data is never touched, and every test starts from empty sheets.
- Fixture: something a test needs, prepared before it and cleaned up after it. A test asks for one by naming it as a parameter (`def test_x(client)`). `scope="session"` means once per whole test run.
- `TRUNCATE`: empties whole sheets at once, faster than deleting rows one by one. Listing `users, sessions` together is allowed even though `sessions` points at `users`.
- Fake secrets in the workflow: they only open a throwaway database that exists for a few minutes inside GitHub's runner, so seeing them gives nobody access to anything real. The real `.env` secrets open your real database and sign real tokens, so they are never committed.
- Green tick / red cross: every job is a check on the PR. Never merge a red PR.

**In my words** (Adithya writes this)
- What this task does, as if explaining to an interviewer: This task added a separate test database and CI. Tests create and delete rows, so they use their own database, and conftest.py refuses to run unless the database name ends in _test. I wrote 6 route tests through the real API covering signup, login, /me, refresh and logout. Then I added a GitHub Actions workflow with two jobs — backend runs pytest, frontend runs lint and build — so every pull request to main shows a green tick or a red cross.

- What I'd check first if it broke: Which job failed (backend or frontend). Then the failed step's log. Then run pytest and npm run build locally — if local passes and CI fails, it's an environment difference like a version or a missing variable. Then check the Postgres service container started. Then check I actually committed and pushed every file CI needs.

- What still confuses me: The runner is fresh every time, so it installs everything from scratch. I understand caches speed that up, but I don't know whether a stale cache can make CI fail or only make it slower.

---

### Task 12: Connect the sign-up and log-in screens to the real backend
**What was built**
- `backend/app/main.py`: one `/api` router holds every route (`/api/health`, `/api/health/db`, `/api/auth/...`), and the app includes it once (D17).
- `backend/app/auth/routes.py`: the refresh cookie's path is now `/api/auth`, in one constant (`REFRESH_COOKIE_PATH`) used both when setting and when deleting it.
- `backend/tests/test_health.py`, `backend/tests/test_auth_routes.py`: the same tests on the new `/api` paths.
- `frontend/package.json`: react-router 8.5.0 (declarative mode).
- `frontend/vite.config.ts`: the dev server passes `/api/...` on to FastAPI at `127.0.0.1:8000` (the proxy).
- `frontend/src/lib/api.ts`: the one place that talks to the backend.
  - `accessToken`: a plain variable, memory only (D16). A reload forgets it.
  - `api()`: sends a request with `Authorization: Bearer <token>`. On a 401 with a token, it refreshes once and retries. If the refresh says the session is over, it logs out.
  - `refresh()`: only one refresh runs at a time; others wait for the same one. If it gets 401, it waits 300 ms and tries once more, because another tab may have just swapped the cookie.
  - `ApiError` and `isUnreachable()`: status 0 (no answer) or any 5xx (Vite answers 502 when FastAPI is stopped) means "can't reach Parley".
- `frontend/src/features/auth/useAuth.ts`: the shared `AuthContext` and the `useAuth()` hook (kept out of the `.tsx` file so the react-refresh lint rule stays happy).
- `frontend/src/features/auth/AuthProvider.tsx`: holds the logged-in user. On page load: refresh, then `/api/auth/me`, with a loading screen meanwhile. Gives every screen `login`, `signup` and `logout`.
- `frontend/src/main.tsx`: wraps the app in `BrowserRouter` and `AuthProvider`.
- `frontend/src/App.tsx`: the pages. `/` is the chat screen; logged out, it sends you to `/login`. Logged in, `/login` and `/signup` send you to `/`. Unknown addresses go to `/`.
- `frontend/src/features/auth/serverErrors.ts`: turns a failed request into form messages: 401 "Wrong email or password." (under password), 409 "That email is already taken." (under email), 422 per field, and "Can't reach Parley. Try again." above the button.
- `LoginScreen.tsx`, `SignupScreen.tsx`: call the real API. `AuthCard.tsx`: the "Sign up" / "Log in" switch is now a router link.
- `ChatScreen.tsx`, `ChatColumn.tsx`, `IconRail.tsx`: the profile shows the real name. Log out calls the API. Chats stay fake until T15.

**New ideas**
- Proxy: the Vite dev server passes `/api` requests on to FastAPI, so the browser sees one site and the cookie needs no cross-site settings. Nginx does the same job later (T26).
- Router: shows a different page for each address (`/login`, `/signup`, `/`), and lets the back button and reloads work.
- Route guard: a page that sends you elsewhere if you're not allowed there (for example `/` to `/login` when logged out).
- Context: a way to share one value (here, the logged-in user) with every screen without passing it down by hand.
- Token in memory: a reload loses it on purpose; the httpOnly refresh cookie brings it back. Scripts on the page can't steal what isn't stored anywhere.
- Single-flight refresh: many requests can fail with 401 at once, but only one refresh runs; the rest wait for its answer.
- The two-tab race: both tabs share one cookie. If one tab rotates it, the other's refresh gets 401; waiting 300 ms and retrying sends the newest cookie.

**In my words** (draft by Claude Code, Adithya keeps or edits)
- What this task does: the screens now use real accounts. Everything goes through `/api` on one address, the access token stays in memory, and the refresh cookie logs you back in after a reload.
- What I'd check first if it broke: the Network tab in DevTools. Does `/api/auth/refresh` return 200, and is the `refresh_token` cookie there with path `/api/auth`? Then whether FastAPI is running on port 8000.
- What still confuses me: how the "401, refresh, retry" path will behave once real chats load in T15, since nothing on the chat screen uses the token yet.


---

### Task 13: Chat tables: chats, chat members, messages
**What was built**
- `backend/app/chats/models.py`: two new sheets.
  - `Chat`: one row per conversation. `kind` is `direct` or `group` (the database refuses anything else). `direct_key` holds the two user ids, sorted and joined with ":", and is UNIQUE, so two people can't get two direct chats (D18). `last_seq` is the counter: the last message number handed out in this chat.
  - `ChatMember`: one row per person per chat. The key is the pair (`chat_id`, `user_id`). It holds the two tick bookmarks, `delivered_up_to` and `read_up_to` (D9). `user_id` has its own index, for "list my chats".
- `backend/app/messages/models.py`: `Message`, one row per message, numbered `seq` #1, #2, #3 inside its chat.
  - UNIQUE (`chat_id`, `seq`): no two #8s in one chat.
  - UNIQUE (`sender_id`, `client_msg_id`): a retried send is never saved twice.
  - `sender_id` has no CASCADE, so deleting a user never quietly deletes messages in other people's chats.
- `backend/app/messages/service.py`:
  - `add_message()`: takes the next number with one `UPDATE chats SET last_seq = last_seq + 1 ... RETURNING last_seq`, which locks the chat's row until the commit. Then it saves the message in the same transaction. If the same `client_msg_id` was already saved, it returns that first copy instead. If two copies arrive at once and the database refuses the second, it rolls back (undoing the +1, so no number is skipped) and returns the first.
  - `_find_sent()`: finds a message by sender and `client_msg_id`.
- `backend/migrations/versions/4b9f0a0b2f7b_create_chats_chat_members_messages.py`: builds the three sheets. `migrations/env.py` now loads every models file, so Alembic sees all the tables.
- `backend/app/auth/routes.py`: `_find_session(lock=True)` locks the session row during refresh (`SELECT ... FOR UPDATE`). Two refreshes with the same cookie: the second waits, then finds the old cookie no longer matches, and gets 401.
- `backend/tests/conftest.py`: `_empty_all_tables()` now empties all five sheets. A new `db` fixture gives a database session for tests that skip the routes.
- `backend/tests/test_messages.py`: 4 tests. Three messages get #1, #2, #3. The same `client_msg_id` twice gives one row and uses one number. Two chats count separately. Two senders at the same moment (two threads) get different numbers.
- `backend/tests/test_auth_routes.py`: two refreshes with the same cookie at the same moment: one gets 200, the other 401.
- `DECISIONS.md`: D18 (how message numbers are kept safe).

**New ideas**
- Per-chat numbers (`seq`): each chat counts its own messages #1, #2, #3. Apps sort by this number, not by time, because two clocks can disagree.
- Counter column (`last_seq`): the chat row remembers the last number it handed out. The next sender adds 1 to it.
- Row lock: an `UPDATE` (or `SELECT ... FOR UPDATE`) locks the row until the commit. A second request for the same row waits, then sees the saved value.
- Transaction: a group of changes saved together or not at all. The +1 and the new message are one transaction, so a failed save never skips a number.
- Composite key: a key made of two columns. (`chat_id`, `user_id`) means one row per person per chat.
- Idempotent send: sending the same message twice has the same effect as sending it once, thanks to `client_msg_id`.
- Race condition: two requests at the same moment that both read before either writes. The lock turns "both at once" into "one after the other".

**In my words** (Adithya writes this)
What this task does:

Adds three tables for real conversations: chats (one per conversation), chat_members (who's in which chat), messages (one row per message, numbered #1, #2, #3 inside its chat).

add_message() takes the next number safely — it locks the chat's row, adds 1, and saves the message in the same transaction. Two people sending at once get #8 and #9, never both #8. If saving fails, the +1 is undone, so no numbers are skipped.

It also fixes the two-tab refresh race from T12: the session row is locked during refresh, so the second tab waits and gets 401 instead of both winning.

What you'd check first:

Did the migration run? alembic upgrade head, then \dt — all 6 tables there?

Are the rules there? \d messages — both unique constraints?

Run pytest tests/test_messages.py — numbering tests fail → problem is in add_message. Concurrency test flaky → the lock.

Tests pass alone but fail together → the db fixture isn't emptying all 5 tables.

What still confuses me:

The two bookmark columns (delivered_up_to, read_up_to) exist but nothing writes to them yet. I get the idea — highest number a person has read — but not how they become read ticks in the UI. That's T14/T15.

---

### Task 14: Start a chat, send a message, load history 30 at a time
**What was built**
- `backend/app/messages/service.py`: `add_message()` now returns `(message, created)`. `created` is `False` for a resend, so the route can answer 200 instead of 201. Sending #N also moves the sender's own `read_up_to` to N, in the same save, so your own messages are never unread for you.
- `backend/app/chats/schemas.py`: what "start a chat" takes (`StartDirectChatRequest`: an email, trimmed and lowercased) and what one row of the chat list looks like (`ChatOut`: id, kind, name, last message, unread; `LastMessageOut`: number, first 100 letters, time).
- `backend/app/chats/service.py`:
  - `direct_key()`: the two user ids, sorted and joined with ":", so Ana+Ben and Ben+Ana give the same label.
  - `get_or_create_direct_chat()`: finds the chat with that label, or makes it with both people in `chat_members`. If two clicks land at once, the UNIQUE `direct_key` refuses the second; it rolls back and returns the first. Returns `(chat, created)`.
  - `get_member()`: this person's row in this chat, or None (not in it, or no such chat).
  - `list_my_chats()`: every chat I have a row in, with the other person's name, the last message (the one numbered `last_seq`), and `unread = last_seq - read_up_to`. Newest message first; an empty chat counts from when it was made.
- `backend/app/chats/routes.py`: `POST /api/chats/direct` (201 new, 200 already there, 400 your own email, 404 unknown email; replies with a chat-list row) and `GET /api/chats`.
- `backend/app/messages/schemas.py`: `SendMessageRequest` (`client_msg_id` + body trimmed, 1 to 4000 letters), `MessageOut`, and `MessagePage` (`messages` + `has_more`).
- `backend/app/messages/routes.py`:
  - `_check_member()`: 404 "Chat not found" if you have no row in the chat. The same reply for a real chat you're not in and a made-up id.
  - `POST /api/chats/{chat_id}/messages`: calls `add_message`; 201 new, 200 resend with the first copy.
  - `GET /api/chats/{chat_id}/messages?before=N&limit=30`: messages numbered below N, newest first. Asks for `limit + 1`; if the extra comes back, `has_more` is true. `limit` is 1 to 100 (101 gives 422).
- `backend/app/main.py`: both new routers plugged into the `/api` router.
- `backend/tests/conftest.py`: a `sign_up` fixture. `sign_up("Ana")` makes ana@example.com and returns her login header.
- `backend/tests/test_messages.py`: unpacks the new `(message, created)` pair, plus a test that the sender's `read_up_to` moves and the other person's doesn't.
- `backend/tests/test_chat_routes.py`: 7 tests. Start twice (from either side) gives one chat; 400/404; login needed; two clicks at once (the first look is made to miss on purpose); both people see the other's name; newest first; last message preview and unread.
- `backend/tests/test_message_routes.py`: 7 tests. Resend gives 200 and one copy; trim and 1 to 4000 letters; a stranger and a made-up id get the same 404; login needed; 70 messages page as #70-#41, #40-#11, #10-#1; `limit`; and the Ana / Ben / Cara story.

**New ideas**
- Paging by number (`before=N`): "the 30 below #41", anchored to a message number. "Page 2" counts from the newest, so one new message shifts every page and you'd see a message twice.
- `has_more` with one extra row: ask for 31; getting 31 back means there's more above.
- 404 instead of 403: "not your chat" and "no such chat" look the same, so nobody can go fishing for real chat ids.
- The screens aren't the lock: anyone logged in can send any request by hand (`/docs`, curl), so every route checks `chat_members` itself.
- Get-or-create: look first, make it if missing, and if the database refuses (someone else made it a moment ago), use theirs.
- One status code per outcome: 201 "made something new", 200 "already had it".
- Access tokens expire after 15 minutes: in `/docs` that shows as 401 "Not logged in", and logging in again fixes it. The real app refreshes by itself (T12).
- `client_msg_id` counts per sender: Ana's `1111...` and Ben's `1111...` are two different messages.

**In my words** (Adithya writes this)
- What this task does, as if explaining to an interviewer: This task added the routes that use the new tables: start a chat, send a message, and load history. POST /api/chats/direct takes an email and returns the direct chat — 201 if it made it, 200 if it already existed; if two clicks land at once, the UNIQUE direct_key refuses the second and returns the first. POST /api/chats/{id}/messages saves a message — 201 new, 200 for a resend with the same client_msg_id — and moves the sender's own read_up_to, so your own messages are never unread to you. GET /api/chats/{id}/messages loads history 30 at a time, newest first, paged by message number (before=N) rather than page number, asking for limit+1 to set has_more. Every route checks chat_members itself, because anyone can call the API by hand, and "not your chat" and "no such chat" both return 404 so nobody can fish for real chat ids.

- What I'd check first if it broke:
- What still confuses me:


---

### Task 15: Real chats on the screen
**What was built**
- `frontend/src/features/chat/types.ts`: the shapes the backend sends (`ChatSummary`, `ServerMessage`, `MessagePage`) and the on-screen `Message`, which has a `status` (sending, failed, sent) and no number until the server answers. `fromServer()` turns one into the other. `tintFor()` picks an avatar color from the chat id, so a chat keeps its color. `Tint` and `Tick` moved here from `fake.ts`.
- `frontend/src/features/chat/time.ts`: server times are UTC; `clockTime()` shows "11:15" in your own time zone, and `listTime()` shows "11:15", "Yesterday" or "15.09" for the chat list.
- `frontend/src/features/chat/useMessages.ts`: one open chat's messages. Loads the newest 30 and flips them (oldest on top). `loadOlder()` asks for `before=<smallest number on screen>` until `has_more` is false. `send()` makes a fresh `crypto.randomUUID()`, shows the message at once, then swaps in the server's copy (matched by `client_msg_id`). `retry()` sends again with the same id.
- `frontend/src/features/chat/NewChatBox.tsx`: the small box under "+". Checks the email in the browser, then `POST /api/chats/direct`. Errors: 404 "No Parley account with that email.", 400 "That's you.", backend down "Can't reach Parley."
- `ChatScreen.tsx`: loads `GET /api/chats`, opens the first chat, adds a new chat to the list, and moves a chat to the top when you send in it. Sending also sets that chat's unread to 0, matching the server's T14 rule (your reply means you've read everything above it). Just opening a chat doesn't clear it yet (that's T18).
- `ChatColumn.tsx`, `ChatRow.tsx`: the real list, "Loading chats...", "Start your first chat" with a "+" when empty, and real times and previews.
- `Conversation.tsx`: shows the messages, loads older ones when you scroll near the top, and keeps the same message in view so nothing jumps. `key={chat.id}` gives each chat a fresh Conversation.
- `MessageBubble.tsx`: a "sending" look (faded, small clock), one grey tick once saved, and "Not sent, tap to retry" on failure.
- `components/Ticks.tsx`: a new "sending" clock. `SidePanel.tsx`: real name and "2 members"; file tiles stay fake. `IconRail.tsx`, `Avatar.tsx`: no fake data left.
- `frontend/src/data/fake.ts`: cut down to the side panel's fake file numbers only.

**New ideas**
- Optimistic send: show the message before the server answers, like WhatsApp's little clock, then swap in the server's copy.
- Idempotent retry: the retry reuses the same `client_msg_id`, so if the first try actually reached the server, the server returns that copy instead of saving a second one.
- Cursor paging on screen: ask for messages "below #41", not "page 2", so new messages never shift what you get and nothing shows twice.
- Scroll anchoring: before older messages go in on top, remember how far you were from the bottom; after, put the scroll back the same distance from the bottom.
- UTC on the server, local time in the browser: the server stores one clock for everyone; each browser turns it into its own time zone.
- A `key` resets a component: a new chat id means React throws away the old Conversation and its messages and starts fresh.
- Old answers are ignored: if you switch chats before a request finishes, the `ignore` flag drops its answer.

**In my words** (Adithya writes this)
- What this task does, as if explaining to an interviewer: This task connected the chat screen to the real backend. The chat list loads from GET /api/chats with real names, previews, times and unread counts. Opening a chat loads the newest 30 messages from GET /api/chats/{id}/messages, flips them so the oldest is at the top, and loads older ones with before=<smallest number on screen> when you scroll up. Sending is optimistic: the message appears at once with a small clock, then swaps in the server's copy when the answer arrives, matched by client_msg_id. A failed send shows "Not sent, tap to retry", and the retry reuses the same client_msg_id so a message that actually reached the server isn't saved twice. The new-chat box under "+" takes an email and calls POST /api/chats/direct.

- What I'd check first if it broke: An empty chat list with a 401 means the token expired. A message stuck on "sending" means checking the Network tab — did POST /api/chats/{id}/messages return 201 or 200, or no request at all? A message showing twice means the swap-back by client_msg_id isn't matching. Scrolling up that jumps means the scroll-anchor math is wrong. Wrong times mean the browser isn't converting the UTC strings (ending in Z) to local time.

- What still confuses me: Optimistic send shows the message before the server answers, then swaps in the server's copy. I understand the normal swap. What I'm not sure about: if the user switches to another chat while a message is still sending, does the swap happen correctly when the answer arrives, or does the ignore flag drop it and leave the message stuck on the clock?

---

### Task 16: The live connection (WebSocket) with a one-time ticket
**What was built**
- `backend/requirements.txt`: `websockets==17.3`. uvicorn finds it by itself and can then speak WebSocket as well as HTTP.
- `backend/app/live/tickets.py`: the ticket list, kept in memory for now (D19).
  - `issue()`: makes a random ticket (`secrets.token_urlsafe`) for this user that dies in 30 seconds. It also throws out stale tickets nobody used, so the list doesn't grow forever.
  - `redeem()`: takes the ticket out first, then checks it, so it works only once. An unknown, used or expired ticket gives None.
  - A thread lock: the ticket route runs in a worker thread and the live line on the async side, so two of them could touch the list at the same moment.
  - `_now()`: a clock that only moves forward (`time.monotonic`). Tests swap it to fake the time.
- `backend/app/live/manager.py`: the switchboard, `lines`: user id â†’ that user's open lines, one per tab.
  - `connect()`, `disconnect()`: add or remove one line. When a user's last line closes, their row goes.
  - `send_to_user()`: sends an event down every open tab of one user. Not used yet (T17).
  - No lock: only the async side touches it, and that side only switches at an `await`.
- `backend/app/live/routes.py`:
  - `POST /api/live/ticket`: needs the access token, replies `{ticket, expires_in: 30}` (`TicketOut`).
  - WebSocket `/api/live?ticket=...` (`live_line()`): redeems the ticket and picks up. A bad, used, expired or missing ticket: hang up with 4401. A good one: put on the switchboard, sent `{"type": "hello", "data": {"user_id": ...}}`, and held open. `finally` takes it off the switchboard however the line ends.
- `backend/app/main.py`: the live router plugged into `/api`.
- `backend/tests/test_live.py`: 5 tests. The ticket route needs a login; a ticket works once (and a made-up one is refused); an expired ticket is refused (clock faked 31 seconds ahead); `hello` carries my id; two tabs give 2 lines, closing one leaves 1, closing both takes the user off the switchboard.
- `frontend/vite.config.ts`: `ws: true`, so the proxy passes WebSocket lines through as well as normal requests.
- `frontend/src/lib/live.ts`: `useLiveConnection()` gets a ticket, opens `ws://<same site>/api/live?ticket=...`, returns true after `hello` and false when the line closes. It closes the line when the screen goes away. No auto-reconnect yet (T19).
- `ChatScreen.tsx`: opens the line. This screen only shows while logged in, so log-in opens it and log-out closes it.
- `ChatColumn.tsx`, `Avatar.tsx`: the dot on my avatar is real now: green when connected, grey when not. `Avatar` takes `status` ("online" or "offline") instead of `online`.

**New ideas**
- WebSocket: a line that stays open, so the server can speak first. HTTP is letters (ask, answer, done); a WebSocket is a phone call.
- One-time ticket: a browser can't put an "Authorization" header on a WebSocket, and addresses end up in logs. So the app trades its token for a ticket that works once and dies in 30 seconds, and only the ticket goes in the address.
- Close codes: a number that says why a line was hung up. Apps can use 4000 to 4999; 4401 means "not logged in". The server must pick up before hanging up, or the browser only sees 1006 ("failed").
- Switchboard: user id â†’ a set of open lines. A set, because one person can have several tabs.
- Thread lock vs. async: a normal `def` route runs in a worker thread, an `async def` one on the async side. Data touched from both needs a lock. Data touched only from the async side doesn't, because it only switches at an `await`.
- `finally`: runs however a block ends (normally, with an error, or cancelled), so a closed tab never stays on the switchboard.
- Faking the clock: `monkeypatch` swaps a function for one test and puts it back afterwards.
- In memory for now: a second backend copy wouldn't see these tickets or lines. They move to Redis in T21 (D19).

**In my words** (Adithya writes this)
- What this task does, as if explaining to an interviewer: This task added a live WebSocket line between the browser and the server, so the server can push events instead of only answering requests. Because a browser can't put an Authorization header on a WebSocket and URLs end up in logs, the app trades its access token for a one-time ticket (POST /api/live/ticket, 30-second lifetime), then opens ws://.../api/live?ticket=... with only the ticket in the address. redeem() removes the ticket before checking it, so it works exactly once. On the server, a switchboard (manager.py) maps user id to a set of open lines — one per tab — and removes the user when the last tab closes. A finally block takes the line off the switchboard however it ends. Bad, used, expired or missing tickets all close with 4401. The avatar dot on the screen is green when connected, grey when not.

- What I'd check first if it broke: The avatar dot staying grey means checking the Network tab's Socket filter — did /api/live?ticket=... open and receive hello? A 4401 means the ticket expired (30 s) or was already used, so ask for a new one instead of reusing it. A 1006 instead of 4401 usually means the server closed before accepting the WebSocket — FastAPI needs await websocket.accept() even when refusing. A line that opens but never gets hello usually means the route crashed after connect — check the uvicorn log. A closed tab still on the switchboard means the finally block isn't running.

- What still confuses me: Nothing blocking right now. The two-backend question I had is answered: the ticket fails first (a ticket issued on copy A and a line landing on copy B gives 4401 at log-in), and a live send fails silently (Ana's message on copy A never reaches Ben's line on copy B, so he only sees it after a reload). T21 fixes both with Redis for tickets and pub/sub for pushes — the open lines stay in whichever copy accepted them.
