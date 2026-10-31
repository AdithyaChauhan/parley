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
- `backend/app/live/manager.py`: the switchboard, `lines`: user id → that user's open lines, one per tab.
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
- Switchboard: user id → a set of open lines. A set, because one person can have several tabs.
- Thread lock vs. async: a normal `def` route runs in a worker thread, an `async def` one on the async side. Data touched from both needs a lock. Data touched only from the async side doesn't, because it only switches at an `await`.
- `finally`: runs however a block ends (normally, with an error, or cancelled), so a closed tab never stays on the switchboard.
- Faking the clock: `monkeypatch` swaps a function for one test and puts it back afterwards.
- In memory for now: a second backend copy wouldn't see these tickets or lines. They move to Redis in T21 (D19).

**In my words** (Adithya writes this)
- What this task does, as if explaining to an interviewer: This task added a live WebSocket line between the browser and the server, so the server can push events instead of only answering requests. Because a browser can't put an Authorization header on a WebSocket and URLs end up in logs, the app trades its access token for a one-time ticket (POST /api/live/ticket, 30-second lifetime), then opens ws://.../api/live?ticket=... with only the ticket in the address. redeem() removes the ticket before checking it, so it works exactly once. On the server, a switchboard (manager.py) maps user id to a set of open lines — one per tab — and removes the user when the last tab closes. A finally block takes the line off the switchboard however it ends. Bad, used, expired or missing tickets all close with 4401. The avatar dot on the screen is green when connected, grey when not.

- What I'd check first if it broke: The avatar dot staying grey means checking the Network tab's Socket filter — did /api/live?ticket=... open and receive hello? A 4401 means the ticket expired (30 s) or was already used, so ask for a new one instead of reusing it. A 1006 instead of 4401 usually means the server closed before accepting the WebSocket — FastAPI needs await websocket.accept() even when refusing. A line that opens but never gets hello usually means the route crashed after connect — check the uvicorn log. A closed tab still on the switchboard means the finally block isn't running.

- What still confuses me: Nothing blocking right now. The two-backend question I had is answered: the ticket fails first (a ticket issued on copy A and a line landing on copy B gives 4401 at log-in), and a live send fails silently (Ana's message on copy A never reaches Ben's line on copy B, so he only sees it after a reload). T21 fixes both with Redis for tickets and pub/sub for pushes — the open lines stay in whichever copy accepted them.

---

### Task 17: Messages arrive instantly, and two ticks when delivered
**What was built**
- `backend/app/live/manager.py`:
  - `send_to_user()` now tries each tab on its own. A tab whose send fails is dropped, and the others still get the event. The event is turned into text once, before the loop, so a mistake in the event can't be blamed on the tabs.
  - `send_to_users()`: the same event to several people.
  - `push_from_thread()`: for normal (`def`) routes, which run in a worker thread. Hands the push to the async side with `anyio.from_thread.run` and waits. Never raises: a failed push is only logged, because the message is already saved (D20).
- `backend/app/chats/service.py`:
  - `member_ids()`: everyone in a chat, meaning who its live events go to.
  - `mark_delivered()`: moves a person's `delivered_up_to` forward to `seq`, capped at the chat's `last_seq`. One `UPDATE` that only matches a member whose bookmark is behind, so non-members and steps backwards change nothing. Returns the new value, or None if nothing moved.
- `backend/app/messages/routes.py`: after a new message is saved (201), pushes `message.new` to everyone in the chat, the sender's other tabs too. A resend (200) pushes nothing. The history reply gains `members`.
- `backend/app/messages/schemas.py`: `MemberOut` (user id and both bookmarks) and `MessagePage.members`.
- `backend/app/live/routes.py`: the line now reads events from the app (`EventIn`, `DeliveredIn`). `_handle()` ignores anything broken or unknown, so a bad event can't knock the line down. A `delivered` event runs `_save_delivered()` in a worker thread (`anyio.to_thread.run_sync`) with its own short database session. If the bookmark moved, a `receipt` goes to the other people in the chat.
- `backend/tests/conftest.py`: the `client` fixture uses `with TestClient(app)`, so the HTTP requests and live lines in one test share one event loop.
- `backend/tests/test_live_messages.py`: 6 tests. `message.new` reaches Ben; `delivered` gives Ana a `receipt` and shows in the history; never backwards or past `last_seq`; a non-member is ignored; a dead line is dropped while the other tab still gets the event; a resend pushes nothing.
- `.github/workflows/ci.yml`: `timeout-minutes: 10` on both jobs, so a stuck live test can't hang CI for 6 hours.
- `frontend/src/lib/live.ts`: `useLiveEvents()` lets any component hear pushed events. `reportDelivered()` sends `delivered`, remembers the highest number per chat, and repeats it when the line opens (the chat list often loads first).
- `frontend/src/features/chat/types.ts`: `MemberBookmarks`, `MessagePage.members`, the `LiveEvent` shapes, and `Message.id`.
- `frontend/src/features/chat/useMessages.ts`: keeps saved messages (merged by id, in number order) apart from my unsaved ones. Takes in `message.new` for the open chat with no doubles, keeps the other person's `delivered_up_to` (from history and receipts), and reports `delivered` after loading history.
- `Conversation.tsx`, `MessageBubble.tsx`: my message #N shows ✓✓ when the other person's `delivered_up_to` is N or more.
- `ChatScreen.tsx`: a pushed message moves its chat to the top (+1 unread if it's theirs and the chat isn't open). A message from a chat I don't have yet reloads the list. The chat list reports `delivered` for each chat's newest message. My unsent messages ("sending" or "Not sent") are kept here, per chat, so they survive switching chats.

**New ideas**
- Push after save: the server saves first (D9), then pushes to everyone's open lines. A failed push loses nothing, because the message is in the database (T19 catches up).
- Worker thread and async side, both ways: `anyio.from_thread.run` (a `def` route hands work to the async side) and `anyio.to_thread.run_sync` (the async line hands database work to a worker thread).
- Bookmarks instead of ticks per message: one number per person per chat. "My #N is ✓✓ when their delivered_up_to is N or more."
- Forward-only bookmark: a conditional `UPDATE` (`WHERE delivered_up_to < target`). A late or repeated report can never undo progress, and the row lock makes two reports at once safe.
- Delivered means "on the device": reported when a message reaches the app (live, history or chat list), not when it's read (T18).
- No doubles: my own message arrives twice (the send's reply and the push). Matching by id and client_msg_id shows it once.
- Testing "nothing happened": you can't wait for silence, so send a marker and check it's the next thing to arrive.
- Two users on one laptop: a normal window and an Incognito window, because tabs in the same window share cookies.

**In my words** (Adithya writes this)
- What this task does, as if explaining to an interviewer: This task made messages arrive instantly on the other person's screen, and shows the sender two ticks once the other device has the message. After a new message is saved, the server pushes message.new to every member's open tabs — including the sender's other tabs — while a resend pushes nothing. A failed push loses nothing, because the message is already saved and T19 will catch up missed ones. Each chat_member row has a delivered_up_to number; when a message reaches a device, the app sends a delivered event, the server moves that bookmark forward with a conditional UPDATE that only matches when the bookmark is behind, and sends a receipt to the other people. My message #N shows two ticks when the other person's delivered_up_to is N or more. No tick is stored per message — just one number per person per chat, and the number can only move forward, so a late or repeated report can never undo progress. Delivered means "on the device", not "read" — read is T18.

- What I'd check first if it broke: No push arriving means checking the Network tab's Socket filter — is the line open, and did message.new arrive? No two ticks means checking delivered_up_to in GET /api/chats/{id}/messages under members — if it's lower than the message's seq, the delivered report never reached the server. A message showing twice means the merge by id and client_msg_id isn't matching the optimistic copy with the pushed copy. CI hanging means checking which step hung, since timeout-minutes should now kill a stuck live test. A crash during push would mean push_from_thread raised, which it should never do, since a failed push must only be logged.

- What still confuses me: When the chat list loads, reportDelivered() runs for each chat's newest message, which moves that person's delivered_up_to to the newest number at once — including messages they haven't scrolled to. I think that's right, because delivered means "reached the device" and the preview itself is evidence it reached the device. But I want to be sure that when T18 arrives, this doesn't accidentally get treated as "read". Delivered and read need to stay separate, and the line between them is the thing I'm watching.

---

### Task 18: Read ticks (teal) and "typing..."
**What was built**
- `backend/app/chats/service.py`:
  - `Bookmarks`: a named pair `(delivered_up_to, read_up_to)`. Both `mark_*` functions return it, or None if nothing moved.
  - `_capped()`: the "never past `last_seq`" rule, shared by both.
  - `mark_read()`: a forward-only `UPDATE` on `read_up_to` (members only, capped at `last_seq`). It also lifts `delivered_up_to` with `GREATEST`, so reading never pulls "delivered" back.
- `backend/app/messages/service.py`: a send now moves both of the sender's bookmarks, not just `read_up_to`.
- `backend/app/live/routes.py`:
  - `_handle()` only sorts events: `delivered` and `read` go to `_on_bookmark()`, `typing` to `_on_typing()`, anything else is ignored.
  - `_on_bookmark()`: moves the bookmark, then sends a `receipt` with both bookmarks to the others in the chat (D20). The `delivered` receipt carries both now too.
  - `_on_typing()`: drops a `typing` that comes within 1 s of the last one from the same line (before touching the database), checks the person is in the chat, and passes `{chat_id, user_id}` to the others. Nothing is saved.
  - `_Line`: what the server remembers about one open line (whose it is, when its last `typing` got through). `_others()`: the others in a chat, or nobody for a non-member.
- `backend/tests/test_live_messages.py`: 7 new tests (13 in the file). `read` moves both bookmarks and the receipt carries both; `read` never goes backwards or past `last_seq`; `read` never pulls "delivered" back; a non-member's `read` and `typing` are ignored; `typing` reaches Ana but not Ben; a second `typing` inside 1 s is dropped (and gets through after a faked 1.1 s); the sender's `delivered_up_to` moves on send. Two T17 tests updated for the "both bookmarks" receipt.
- `frontend/src/lib/live.ts`: `reportRead()` (the highest number per chat, sent again when the line opens, like `delivered`), `sendTyping()` (at most once every 3 s per chat) and `windowInFront()` (the tab is showing and the window has focus).
- `frontend/src/features/chat/types.ts`: the receipt has `read_up_to`, and there's a new `typing` event.
- `frontend/src/features/chat/useMessages.ts`: also keeps the other person's `read_up_to` (from history and receipts), and `newestSeq`.
- `frontend/src/features/chat/useTyping.ts` (new): chat id → who is typing there. Hidden 5 s after their last `typing`, or as soon as their message arrives.
- `frontend/src/features/chat/Conversation.tsx`:
  - Sends `read` only when the chat is showing, the window is in front and the newest message is on screen. Checks again on load, on a new message, on scroll, and when you come back to the window or tab.
  - Picks ✓, grey ✓✓ or teal ✓✓ for each of my messages.
  - Shows "<name> is typing..." with the bouncing dots, and stays at the bottom when it appears.
  - On a phone, jumps to the newest message when the chat comes into view (it loaded while hidden, and a hidden list can't scroll). This was an old T15 bug that T18 made visible.
- `MessageBubble.tsx`: `receipt` ("delivered", "read" or none) replaces `delivered`.
- `MessageBox.tsx`: `onTyping` on every key, but not when the box is emptied.
- `ChatScreen.tsx`: `markRead()` sets a chat's unread to 0 when its conversation sends `read`. Their new message always adds 1; if you're looking at that chat, the read check clears it again before the screen is drawn.
- `ChatColumn.tsx`, `ChatRow.tsx`: "typing..." replaces the preview in the chat list.

**New ideas**
- Delivered vs read: delivered = "it's on my device" (chat list, history, live push). Read = "it was on my screen": open chat, window in front, newest message in view. The chat list never sends read.
- Read implies delivered: `GREATEST(delivered_up_to, n)` lifts "delivered" without ever lowering it.
- Three ticks from two numbers: my #N is teal ✓✓ if their `read_up_to` ≥ N, grey ✓✓ if their `delivered_up_to` ≥ N, else ✓.
- Short-lived events: "typing" is only true for a few seconds, so it's passed on and never saved. A missed one costs nothing; the next comes in 3 s.
- Two speed limits: the app sends at most every 3 s (being polite), and the server drops anything within 1 s per line (protecting itself, because it can't trust the app). The server's check runs before the database, so spam is cheap.
- Show-for timer: the receiver shows "typing..." for 5 s after the last event. 5 is more than 3, so it stays on while they type and goes away by itself when they stop or close the tab. No "stopped typing" event needed.
- Page visibility and focus: `document.visibilityState` (is the tab showing?) and `document.hasFocus()` (does the window have the keyboard?). The `focus` and `visibilitychange` events tell the app to check again.
- Layout effect: runs after React changes the page but before the browser draws it, so scrolling and clearing the unread count happen with no flash.
- Marker events in tests: you can't wait for "nothing arrived", so send a later event on the same line and check it's the next thing to arrive.

**In my words** (Adithya writes this)
- How the app decides a message is "read" and not just "delivered": Delivered is automatic — anything that puts the message on the device counts (the chat list loading, history loading, or a live push). Read is strict: the chat must be open, the window must be in front (document.visibilityState is "visible" and document.hasFocus() is true), and the newest message must be on screen. The app checks again on load, on a new message, on scroll, and when you come back to the window or tab. The chat list never sends read.

- Why typing is never saved in the database: Because it's only true for a few seconds — saving it would mean a database write on every keystroke for information that's worthless a second later. It's passed to the other person and forgotten. The server drops anything within 1 second of the last one from the same line, before touching the database, so spam is cheap to refuse. The receiver shows "typing..." for 5 seconds after the last event, which is longer than the 3-second send limit, so it stays on while they type and fades by itself when they stop. No "stopped typing" event is needed.

- What Ana's app checks to pick ✓, grey ✓✓ or teal ✓✓: There are two numbers per person per chat, delivered_up_to and read_up_to. For Ana's message #N: if their read_up_to is N or more, it shows teal ✓✓; otherwise if their delivered_up_to is N or more, it shows grey ✓✓; otherwise it shows ✓. Read implies delivered — when someone reads #12, delivered_up_to is lifted to at least 12 too (using GREATEST, so it never goes down).

---

### Task 19: Reconnect and catch up on missed messages
**What was built**
- `backend/app/live/routes.py`:
  - `_save_bookmark()`, `_on_bookmark()`: a `receipt` now goes to everyone in the chat, the reader's own tabs too (D20), so Ben's other tab can clear its unread. `typing` still goes only to the others.
  - `EventIn.data` defaults to `{}`, so a bare `{"type":"ping"}` is a valid event (D21).
  - `_Line.websocket`: the line itself, so an answer can go back to just the tab that asked.
  - `_handle()` answers `ping` with `{"type":"pong","data":{}}`. No database, so it costs almost nothing.
- `backend/app/messages/routes.py`: history takes `after=N`: messages above #N, **oldest first**, and `has_more` means newer ones are waiting. `after=0` starts from #1. `before` with `after` gives 422.
- `backend/app/messages/schemas.py`: `MessagePage` comments explain both directions.
- `backend/tests/test_live_messages.py`: Ben has two tabs, reads in one, and the other gets his own receipt.
- `backend/tests/test_message_routes.py`: catch-up pages come oldest first with the right `has_more`, and `after=0` starts from #1. `before` with `after`, and `after=-1`, give 422.
- `backend/tests/test_live.py`: `ping`, with or without `data`, gets `pong`.
- `frontend/src/lib/live.ts`:
  - `useLiveConnection()` now reconnects by itself and returns `connecting`, `online` or `reconnecting`.
  - Heartbeat: `ping` every 25 s. No `pong` (or no `hello` after opening) within 10 s → `hangUp()`.
  - `lost()`: waits 1, 2, 4 ... up to 30 s, plus 0–1 s of random extra, then tries again with a new ticket. A `hello` resets the wait.
  - The browser's `offline` hangs up at once. `online`, or the tab coming back to the front, tries at once. Never after log-out.
  - `announce()`: one way in for pushed events, `hello`, and my own send's reply.
- `frontend/src/features/chat/useOutbox.ts` (new): my unsent messages per chat. Sends one at a time, in order, each with its original `client_msg_id`. No answer → that message and everything after it are "waiting". A real refusal → "Not sent, tap to retry". Every `hello` sends every chat's waiting messages.
- `frontend/src/features/chat/useMessages.ts`:
  - `gapFree()`: the highest number with no hole below it.
  - `takePage()`: one page in from any direction (merge, bookmarks, "delivered").
  - `catchUp()`: `after=<gapFreeSeq>`, 100 at a time while `has_more`.
  - On `hello`: catch up, or load the normal way if the chat never loaded. A saved message that skips numbers also catches up (the gap check).
  - Their pushed message #N lifts their bookmarks to at least #N, because the server moved them with no receipt when it saved the message (D20). Found in the "Server restart" check: Ana's `r1` stayed at one grey ✓ after Ben's `r2` went out.
  - Sending moved out to `useOutbox`. My unsent copy is hidden once the saved one is on screen.
- `ChatScreen.tsx`: reloads the chat list on every `hello` (`reloadChats()`). `myReadMoved()`: a receipt about me sets unread to the newest number minus my `read_up_to`, and only ever lowers it. Holds the outbox.
- `Conversation.tsx`: "read" reports `gapFreeSeq`. Sends and retries go to the outbox.
- `ChatColumn.tsx`: "Reconnecting..." takes the "available" pill's place while the line is down, at the same height, so nothing jumps.
- `MessageBubble.tsx`: a waiting message is faded, with the clock and "Waiting for connection".
- `types.ts`: the `pong` event and the `waiting` status.

**New ideas**
- Heartbeat: a dead Wi-Fi often doesn't close the line, so silence is the only sign. The app asks "you there?" every 25 s. uvicorn already pings at a lower level, but browser code can't see those pings, so the app needs its own.
- Hang up yourself: on a dead network, a polite close can take minutes, so the app drops the line and moves on.
- Exponential backoff: each failed try waits twice as long (1, 2, 4 ... 30 s), so a server that's down isn't hammered. A good connection resets it.
- Jitter (random extra): after a server restart, every app lost its line at the same moment. 0–1 s of random spreads them out, so they don't all call back in the same second.
- Catch-up by number: messages are numbered with no gaps (D18), so "what did I miss?" is "everything after my highest number". Times would be wrong: clocks disagree, and two messages can share a millisecond.
- The highest number with no hole below it: if I have #20 and #24, catch-up asks `after=20`, not `after=24`.
- Gap check: a message that skips numbers proves something went missing, even while connected.
- Catch up on every `hello`, the first one too: it also covers the moment between the page loading and the line opening.
- Outbox: every send goes through one queue per chat, one at a time, so order is kept. "No answer" waits; "refused" fails.
- Safe to send again: the same `client_msg_id` on every try means a resend after a lost reply gets the first copy back, not a double (D18).
- Browser signals: `online`, `offline` and `visibilitychange` tell the app to act now instead of waiting.
- One way in: my send's reply and a pushed message go through the same listeners, so the chat list, the gap check and "no doubles" work the same for both.
- Receipts to myself: unread = newest number − my `read_up_to`. That works across tabs, and a "delivered" receipt can't wrongly clear unread.
- Sending counts as reading: a message from Ben at #N means Ben's bookmarks are at #N too. The server moves them silently, so the app works it out from the push. Known simplification: after an offline race this can show "read" a few seconds early (D20).

**In my words** (Adithya writes this)
- How the app knows the line is dead:
  Short version: It asks "you there?" and waits for a reply.
  Full version: When Wi-Fi drops, the browser often doesn't know, and the line just sits there looking open. So the app sends a ping every 25 seconds. If the server doesn't answer with a pong within 10 seconds, the app knows the line is dead, hangs up, and starts trying to reconnect.

- How catch-up finds exactly the messages you missed:
  Short version: It asks for everything above its highest safe number.
  Full version: Every message in a chat has a number with no gaps (#1, #2, #3). The app remembers the highest number it has with no holes below it. When it reconnects, it just asks the server "give me everything after this number". This is safer than using times because two phones' clocks can disagree.

- Why waiting messages can be re-sent without making doubles:
  Short version: Each message has a unique ID, so the server ignores copies.
  Full version: Every message gets a unique ID (client_msg_id) the moment you hit send. If you send it while offline, it waits in a queue (the outbox). When it retries, it sends that exact same ID. If the first try actually did reach the server, the server sees the same ID, refuses to save it twice, and just returns the first copy.

---

### Task 20: Online and "last seen", with Redis
**What was built**
- `docker-compose.yml`: a `redis` service (`redis:8.10.2`, the current stable) with a `redis-cli ping` health check. No volume: losing the notes on a restart is fine.
- `.env.example`: `REDIS_URL` (database 0, the app) and `TEST_REDIS_URL` (database 15, tests only).
- `backend/requirements.txt`: `redis==8.1.0` (redis-py). One package, two clients: normal and async (D22).
- `backend/app/config.py`: reads `redis_url`.
- `backend/app/presence/service.py` (new, D5 folder):
  - `tab_alive()`: in one transaction, wipes dead tabs, counts the alive ones, sets this tab's "alive until" to now + 60 s, resets the key's own 60 s timer, and writes `last_seen`. Returns True if no tab was alive before (just came online).
  - `tab_closed()`: in one transaction, removes the tab, wipes dead tabs and writes `last_seen`. Returns True if no tab is left (offline now), including when this tab's time had already run out.
  - `is_online()` and `last_seen()`: for the chat list, with the normal client. `is_online()` wipes dead tabs first.
  - `start()` / `stop()`: make and close the async client. `_now()`: a real clock time that tests can fake.
- `backend/app/main.py`: a `lifespan` that calls `presence.start()` when the server starts and `presence.stop()` when it stops, so the async client lives in the server's own event loop.
- `backend/app/chats/service.py`:
  - `partner_ids()`: everyone who shares at least one chat with a person, once each.
  - `list_my_chats()`: each row gets `other_user_id`, `online` and `last_seen` for the other person in a direct chat.
- `backend/app/chats/schemas.py`: `ChatOut` gains `other_user_id`, `online` and `last_seen`. `other_user_id` wasn't in the brief: without it, the app can't tell which row a `presence` event is about.
- `backend/app/live/routes.py`:
  - `_Line.tab_id`: the server names each line (= each tab).
  - `_tab_alive()`: called on connect (before `hello`) and after every `pong`. Pushes `presence` only when the person just came online.
  - When the line ends: `tab_closed()`, and `presence` (offline) if no tab is left. This goodbye is shielded for up to 5 s, so it isn't cut off when the line is being cancelled.
  - `_push_presence()`: `{user_id, online, last_seen}` to everyone in `partner_ids()`, through this copy's switchboard (T21 adds the other copies).
- `backend/tests/conftest.py`: reads `TEST_REDIS_URL`, refuses anything but database 15, points the app at it, and wipes it (`FLUSHDB`) after each test.
- `backend/tests/test_presence.py` (new, 7 tests): one tab online then offline; close one of two tabs, still online; a silent tab goes offline after a faked 61 s; a ping keeps a tab alive; `last_seen` is the exact (faked) close time; online and offline news reach a partner but not a stranger, and a ping while online is no news; the chat list and `POST /api/chats/direct` show `other_user_id`, `online` and `last_seen`.
- `backend/tests/test_live_messages.py`: 5 tests where Ana's line is open when Ben (or Cara) connects now first read the "came online" event.
- `.github/workflows/ci.yml`: a throwaway Redis service, and both Redis addresses set to database 15.
- `frontend/src/features/chat/types.ts`: chat rows have `other_user_id`, `online`, `last_seen`; a new `presence` event.
- `frontend/src/features/chat/time.ts`: `lastSeenText()`: "last seen today at 11:15", "yesterday at 09:02", "15.09 at 18:40", or "last seen recently". `listTime()` now shares `dayLabel()` with it.
- `ChatRow.tsx`: a green dot on the avatar while the other person is online.
- `Conversation.tsx`: the header gets the avatar (with the dot), and "online" or "last seen ..." under the name.
- `ChatScreen.tsx`: `presence` events update the matching row (by `other_user_id`). While a chat is open, the chat list reloads every 60 s, which catches tabs that went silent without a goodbye.

**New ideas**
- Redis: a whiteboard kept in memory. Very fast, and a note can have a timer after which it wipes itself. PostgreSQL is the filing cabinet: safe and permanent. "Online" changes all the time and is fine to lose, so it lives in Redis (D22).
- Redis databases: one Redis server has numbered databases (0–15). The app uses 0, tests use 15, and the tests refuse any other number before they wipe anything.
- Sorted set: a list of names, each with a number (a "score"), kept in order. Here: tab id → "alive until" time. "Remove everything with a score up to now" wipes every dead tab in one command.
- Per tab, not one flag: one "online" flag breaks with two tabs (closing one says offline) and with a crash (nobody says goodbye). One row per tab with its own "alive until" fixes both.
- Timers instead of goodbyes: a ping every 25 s pushes "alive until" 60 s ahead. A tab that stops pinging simply runs out. The key's own timer means Redis even wipes the whole note if every tab goes silent.
- Transaction (MULTI): Redis runs a list of commands in one go, with nothing from another tab in between. So "count the alive tabs, then add mine" can't be fooled by a second tab doing the same at the same moment.
- Only push changes: a ping while already online is no news, so nothing is pushed. Only "came online" and "went offline" travel.
- Silent crash: nothing happens on the server when a tab's time runs out, so nobody is told. The apps notice at their next 60 s check (up to about 2 minutes in total, D22).
- Event loops and async clients: an async Redis client only works inside the event loop it was made in. So it's made when the app starts (lifespan), not when the file is loaded.
- Order matters: record "online" and push the news before saying `hello`. Then when an app hears `hello`, everyone who needed the news already has it. (A test found this: Ben's line got news meant for before he connected.)
- Shielded cleanup: when a line is cancelled, every `await` in its clean-up would stop at once. A shield lets the goodbye finish, with a 5 s limit so it can never hang.
- Real clock vs forward-only clock: the typing limit uses `time.monotonic()` (only measures gaps). Presence uses `time.time()`, a real time, because `last_seen` is shown to people and every backend copy must agree on it.

**In my words** (Adithya writes this)
- What Redis is, and why "online" lives there and not in PostgreSQL: Redis is a fast, in-memory whiteboard, while PostgreSQL is a slow, permanent filing cabinet. "Online" status changes every few seconds and is fine to lose if the server restarts. Keeping it in PostgreSQL would mean constant, unnecessary disk writes. Redis keeps it in memory and can automatically delete notes after a timer runs out.

- How the "alive until" times handle two tabs and a crash: We don't just have one "online" flag; we keep a separate timer for every tab. If you have two tabs open, closing one leaves the other timer running, so you stay online. If your laptop crashes, you never send a "goodbye", but because every ping pushes your timer 60 seconds into the future, the server just waits for that time to pass and automatically wipes the dead tab.

- How Ben's screen learns that Ana went offline (when she closes the tab, and when her tab goes silent): If Ana closes her tab normally, the server gets a "goodbye", deletes her tab, and instantly pushes a presence event to Ben (so he sees it in about 1 second). If her tab goes silent (a crash), there is no goodbye. The server waits for the 60-second timer to expire, and Ben's app checks the chat list every 60 seconds. So, Ben finds out at his next check, which can take up to about 2 minutes total.

---

### Task 21: Two backend copies, live messages cross between them (Redis pub/sub)
**What was built**
- `backend/app/live/tickets.py`: tickets live in Redis as `ticket:<t>` with a 30 s Redis timer. `redeem()` uses `GETDEL` (read and delete in one step), so any copy can redeem a ticket any copy made, exactly once. The in-memory list, its lock and its clean-up loop are gone.
- `backend/app/config.py`, `main.py`: a `COPY_NAME` setting (default "A"), shown in `GET /api/health` as `"copy"`.
- `backend/app/live/bus.py` (new), the radio:
  - `publish()` (normal client, for normal routes) and `publish_async()` (async client, for the live line) shout an event on `user:<id>` for each person, in one trip to Redis (a pipeline). Neither ever raises: a failed push must not fail a send (D20).
  - `match_lines()`: listen on `user:<id>` exactly while that person has a line on this copy. On subscribe it waits for Redis's "subscribed" confirmation. A lock and "look at the lines right now" stop a closing tab and an opening tab from crossing.
  - `listen()`: one background loop for the copy's whole life. It hands each event it hears to this copy's own lines, wakes up lines waiting for their confirmation, skips bad events, and listens again 1 s after Redis drops (redis-py subscribes to every channel again by itself).
  - `start()` / `stop()`: the listening connection, the lock and the bookkeeping are made in the server's event loop.
- `backend/app/live/manager.py`: only this copy's own lines now. `send_to_user()` sends ready-made text. `send_to_users()` and `push_from_thread()` are gone.
- `backend/app/main.py`: the lifespan also starts the radio and runs `listen()` in the background, and cancels it and closes the radio on the way out.
- `backend/app/live/routes.py`: a new line runs `match_lines()` (listen, confirmed), then "online", then `hello`. Its end runs `match_lines()` inside the shielded goodbye. `receipt`, `typing` and `presence` go through `publish_async()`.
- `backend/app/messages/routes.py`: `message.new` goes through `publish()`. No more hand-off from the worker thread to the async side.
- `frontend/vite.config.ts`: the proxy target comes from `PARLEY_API_PORT` (default 8000), so a second Vite on 5174 can talk to copy B on 8001.
- Tests (67 in all):
  - `test_live.py`: the expiry test lets Redis expire the ticket for real (timer cut to 1 ms with `PEXPIRE`), because Redis's clock can't be faked. New: a ticket sits in Redis with a timer of 30 s or less and is gone once used.
  - `test_health.py`: expects `"copy": "A"`.
  - `test_live_messages.py`: the dead-line test waits for a second push before checking, because delivery now happens in the background.
  - `test_bus.py` (new): a shout published straight into Redis (as another copy would) reaches Ben's line; this copy listens for Ben only while he has a line here (two tabs, close one, close both); bad events are skipped and the next good one still arrives.
- Checked by hand: the listener survives a Redis restart. Two copies (A on 8000 via 5173, B on 8001 via 5174): messages, ticks, typing and online status cross. Stopping copy A turns Ana grey on Ben's screen; starting it again catches Ana up, with nothing lost and no doubles.

**New ideas**
- Several copies of one backend: the same code running two (later many) times, to share the load and survive one copy dying. Anything a copy keeps only in its own memory (tickets, the switchboard) is invisible to the others.
- What can't move and what can: an open line (WebSocket) is stuck to the copy that accepted it. A ticket is just data, so it moves into Redis, where every copy can see it.
- Pub/sub, a radio: `PUBLISH user:<Ben>` shouts on a channel; every connection that did `SUBSCRIBE user:<Ben>` hears it. The sender doesn't know or care where Ben is.
- Channel per person, listened to only where needed: a copy subscribes to `user:<Ben>` while Ben has a line there, so it never hears about people it can't deliver to.
- Pub/sub keeps nothing: a shout nobody hears is gone. That's fine here, because the message is saved first (D9) and the app catches up by number (D21). Pub/sub carries the "now", PostgreSQL keeps the truth.
- Every push goes through the radio, even when both people are on the same copy. One path for everything means no special cases, and the tests exercise the real path.
- Wait for the confirmation: Redis confirms a subscription a moment after we ask. Saying `hello` only after the confirmation means nothing shouted after `hello` can slip past.
- A background task: `listen()` runs alongside everything else for the copy's whole life, started and stopped by the lifespan.
- One bad event mustn't stop the radio: each event is handled inside its own try/except, so the loop goes on for everyone else.
- Atomic "read and delete" (`GETDEL`): two copies trying the same ticket at the same moment can't both win.
- Pub/sub ignores Redis database numbers: channels are shared between database 0 and 15. Harmless here, because user ids are random UUIDs.
- Cookies ignore port numbers: localhost:5173 and localhost:5174 share cookies, so two people need two separate windows (normal + Incognito).

**In my words** (Adithya writes this)
- Why two copies broke live chat before pub/sub: Because a server only knows about WebSockets that are physically connected to it. If Ana was connected to Copy A and Ben was connected to Copy B, Copy A would save Ana's message but look at its own local switchboard, see no Ben, and drop the push. Copy B had Ben's line, but never knew a message existed.

- How a message from copy A reaches Ben's line on copy B: We use Redis as a radio (pub/sub). Copy A saves the message, then publishes (shouts) it to a Redis channel named after Ben. Copy B is subscribed (listening) to Ben's channel because Ben's line is connected there. Copy B hears the event and sends it down Ben's WebSocket.

- Why losing a pub/sub shout is OK in Parley: Because Redis pub/sub doesn't save anything; if nobody hears the shout, it vanishes. That is perfectly fine because we always save the message to PostgreSQL first (the filing cabinet). If the live radio shout is lost, the app just uses its catch-up logic (after=<number>) to ask the database for anything it missed.

### Task 22: Spam limits, and Parley keeps working when Redis is down
**What was built**
- `backend/app/limits/service.py` (new), the limit counter (D24):
  - `Rule` and the six limits in one place: `SEND` (20 per 10 s per user), `LOGIN_EMAIL` (5 tries per 15 min per email), `LOGIN_IP` (30 per 15 min per IP), `SIGNUP_IP` (5 per hour per IP), `START_CHAT` (20 per minute per user), `TICKET` (10 per minute per user).
  - `hit(key, limit, window_seconds)`: the sliding window. One Redis transaction drops times older than the window, adds "now" (with a random name, so two at the same instant are two entries), counts, reads the oldest, and resets the key's timer. Over the limit: it takes "now" back out and returns the seconds until the oldest leaves the window. Returns 0 for "go ahead". Redis down: logs a warning and allows.
  - `clear(key)`: deletes the key (a good log-in wipes its email's tries). Safe when Redis is down.
  - `enforce(rule, who)`: for the routes. A refusal becomes 429 with `Retry-After`.
  - `key(rule, who)`: `limit:send:<id>`, `limit:login_email:<email>`, ...
- `backend/app/auth/routes.py`: sign-up counts per IP. Log-in counts per IP and per email **before** the password check, and a good log-in clears the email's count, so it means "tries since the last good log-in". A locked email gets 429 even with the right password, and never costs a slow hash check. `_ip()` reads `request.client.host` (T26 must set `--proxy-headers`, or every request looks like Nginx).
- `backend/app/messages/routes.py`: the send limit, first in the route, so a flood never reaches the database.
- `backend/app/chats/routes.py`: the start-chat limit (fishing for emails).
- `backend/app/live/routes.py`: the ticket limit; a ticket answers 503 "Live updates unavailable" when Redis is down. An open line whose ping hits a dead Redis logs one warning and closes with 1011 (the app reconnects with its backoff), and the goodbye can't crash.
- `backend/app/presence/service.py`:
  - Both Redis clients give up fast. Out of the box, one call to a dead Redis took 49 s (10 tries with growing waits). Now: at most 1 s to connect. The normal client makes one try (a send waits on it; it swaps a dead connection for a fresh one by itself after a restart). The async client keeps one quick second try, because without it every open line would drop once after a Redis restart.
  - `statuses(user_ids)`: online and last seen for the whole chat list in one trip to Redis (a pipeline), replacing `is_online()` (two calls per row). Redis down: every row is `UNKNOWN` (`online: false`, `last_seen: null`), which the app shows as "last seen recently".
- `backend/app/chats/service.py`: the chat list reads its rows first, then calls `statuses()` once.
- `backend/migrations/env.py`: Alembic's logging set-up no longer silences loggers that already exist (`disable_existing_loggers=False`). The tests run migrations inside the same Python as the app, so before this, no app warning ever reached the test output.
- App:
  - `frontend/src/lib/api.ts`: `ApiError` carries `retryAfter`, read from the `Retry-After` header.
  - `frontend/src/features/chat/useOutbox.ts`: a 429 on a send marks it and everything after it "waiting", sleeps for `Retry-After`, then goes on from the oldest. The queue stays busy while it waits, so nothing overtakes, and each message keeps its `client_msg_id` (no doubles).
  - `frontend/src/features/auth/serverErrors.ts`: "Too many tries. Try again in N minutes." on log-in and sign-up.
  - `frontend/src/features/chat/NewChatBox.tsx`: "Slow down a moment."
  - `frontend/src/features/chat/useMessages.ts`: when the chat list knows a newer message number than the open chat shows, the chat catches up. While the live line is down, the list's 60 s re-check is the only news, so without this the open chat went stale.
  - `frontend/src/features/chat/Conversation.tsx`: when the list brings back an unread count for the chat you're looking at (your "read" waits in the app while the line is down), the chat clears it again, if the newest message is really on screen.
  - `live.ts` didn't change: a failed ticket, 503 included, already counts as "line down".
- Tests (76 in all):
  - `test_limits.py` (new): the 21st send gives 429 with `Retry-After` and works again after the window (the key's timer cut to 1 ms with `PEXPIRE`, as in T21); the refused send was never saved. The 6th try locks the email even with the right password, but not other emails. A good log-in clears the count. Sign-up's per-IP limit. 50 requests at the same moment against a limit of 20: exactly 20 get through.
  - `test_redis_down.py` (new): the normal client points at a dead address with the same give-up-fast settings. A send still gives 201 and the rows are saved, even past a limit of 1, with the warning logged. The chat list gives 200 with online unknown. A ticket gives 503. An open line closes with 1011.
  - `test_message_routes.py`: the 70-message paging test lifts the send limit for itself with `monkeypatch`.
- Checked by hand: 30-odd quick sends: 20 went, one got 429, it and the rest waited and went in order, with no doubles. 6 wrong passwords: "Too many tries", the right password locked too, unlocked by clearing the keys. Redis stopped: Ana sends (a few seconds on Windows), Ben's open chat shows it within a minute without a reload, single tick, "last seen recently", "Reconnecting...". Redis started: both windows online again by themselves, the tick turns double, live messages flow.

**New ideas**
- Rate limit: a cap on how often someone may do something. Over the cap, the server answers 429 "Too many requests" instead of doing the work, and `Retry-After` says how many seconds to wait.
- Sliding window: count only what happened in the last N seconds, measured from now. A sorted set of times does it: drop the ones too old, count the rest. Unlike a fixed "per minute" bucket, there's no edge where 20 at 0:59 and 20 at 1:00 both get through.
- Add, then take back: a Redis transaction can't say "only add if under 20", so every request adds itself first and counts. If it's over, it removes itself. Each request's count includes everyone who came at the same moment, so a 21st can never slip through.
- A timer on the key (`EXPIRE`): once nobody hits it for a whole window, everything in it is too old anyway, so Redis wipes it. Idle keys vanish by themselves.
- What to count per: sends per user (one spammer); wrong passwords per email (guessing one account from many computers); log-ins per IP (one computer guessing many accounts); sign-ups per IP (one computer making many accounts).
- Fail open vs fail closed: when Redis is down, limits let requests through (better a little spam than no chat), but PostgreSQL down still fails, because without it nothing can be saved. A helper may fail open; the truth can't.
- Give up fast: a client that retries for 49 s turns "Redis is down" into "Parley is down". A short connect timeout and few retries keep a dead helper cheap.
- Retries are a trade-off: a quick second try survives an old connection after a restart, but doubles the wait when the server is really gone. Measured both before choosing per client.
- One trip for many: a pipeline sends many commands together and reads all the answers at once, so the chat list costs one Redis trip instead of two per row.
- Logging and Alembic: `fileConfig()` switches off every logger that already exists unless told not to. That hid the app's warnings in tests.
- A lint false alarm: React's lint rule flagged `catchUp()` in an effect, but it only changes state after its first `await`. The rule is switched off for that one line, with the reason written down.
- Windows vs Linux: on Windows, a connection to a port nobody listens on takes about 1 s per address to fail (and `localhost` tries two addresses). On Linux it fails instantly. Using `127.0.0.1` halves it in dev.

**In my words** (Adithya writes this)
- How the sliding window counts the last 10 seconds: Every time you send a message, the app writes down the exact time in Redis. To check the limit, it first deletes any timestamps older than 10 seconds. Then it counts how many are left. If the count is over 20, it deletes your new timestamp and rejects the request. Because the window slides with you, you can't cheat the system by sending 20 messages at the end of a minute and 20 at the start of the next.

- Why limits let requests through when Redis is down, but PostgreSQL doesn't get the same treatment: Redis only holds temporary helpers like spam limits and online dots. If Redis dies, it is better to let a little spam through than to crash the whole app (failing open). PostgreSQL, however, holds the actual messages. If the database is down, we cannot save anything, and a chat app that can't save messages is useless. So we must fail closed and show an error.

- Why a wrong-password limit is per email and also per IP: They stop two different attacks. The per-email limit stops someone from guessing Ana's password from 1,000 different computers. The per-IP limit stops someone from using one computer to guess 1,000 different people's passwords. You need both to block targeted attacks and broad spray attacks.

### Task 22b: Fix: reads and ticks reach the server without the live line
**What was built**
- `backend/app/chats/service.py`: `save_bookmark(db, chat_id, user_id, kind, seq)`, the one function behind both doors (D20). It calls `mark_read` or `mark_delivered` (forward only, never past `last_seq`, read lifts delivered), which commit to PostgreSQL first. Only if the bookmark moved does it build the receipt and push it with `bus.publish` (never raises). If nothing moved, it returns `None` and pushes nothing.
- `backend/app/chats/schemas.py`: one `BookmarkIn` (`seq`, at least 1), used as the HTTP body, and `BookmarksOut` (both bookmarks) for the reply.
- `backend/app/chats/routes.py`: the HTTP door, `POST /api/chats/{chat_id}/delivered` and `/read` with `{"seq": N}`. `_bookmark_door()` looks up the member row (404 for "not your chat" and "no such chat"), calls `save_bookmark`, and returns the bookmarks: the moved ones, or the current ones if nothing moved. No rate limit.
- `backend/app/live/routes.py`: the live line's event is `LiveBookmarkIn(BookmarkIn)`, which only adds `chat_id`. `_save_bookmark` opens a short database session and calls the same `save_bookmark`, in the worker thread, so the receipt now goes out through the normal Redis client. The old receipt-building code is gone.
- App:
  - `frontend/src/lib/live.ts`: every read and delivered goes through `sendBookmark()`. Line open → on the line. Line known to be down (a drop, or a failed connect such as a ticket 503) → the HTTP door. While the line is first connecting → wait, because `hello` sends everything. The app keeps what the server has confirmed per chat, and sends only what's above it: after each drop, when the browser is back online, and on reconnect (where it sends everything again, since a send on a dying line can be lost). `shownUpTo()` gives the highest number this tab has shown in a chat.
  - `frontend/src/features/chat/ChatScreen.tsx`: `withMyReads()` sets each badge to newest − the higher of (the server's read, what this tab has shown), so it never comes back while a read is on its way.
  - `frontend/src/features/chat/Conversation.tsx`: T22's workaround (re-clearing the badge when the list brought it back) is gone; the real fix replaces it.
  - Catch-up pages (including T22's chat-list catch-up) already reported delivered; with the HTTP door, those reports now arrive during an outage too.
  - Added during the task (approved, D24): Ana's ticks during an outage. `ChatScreen.tsx` counts the chat list's 60 s re-checks (`listChecks`) and passes `lineDown` (the line says "Reconnecting..."). In `useMessages.ts`, each re-check makes one `messages?after=<gap-free seq>` request if the list knows a newer message or the line is down. The reply carries both people's bookmarks, so Ana's tick turns teal within about a minute. One check covers both triggers, so they never send two requests, and the outage re-check stops by itself once the line is back.
- Tests (86 in all):
  - `test_bookmark_routes.py` (new): delivered and read move forward only and stop at the last message, read lifts delivered, a non-member or unknown chat gets 404, seq 0 gets 422, the chat list shows unread 0 after an HTTP read, and a bookmark that doesn't move pushes nothing, through the HTTP door and through the live line.
  - `test_redis_down.py`: with Redis down, an HTTP read gives 200, is saved, and the chat list shows no badge. Ana's re-check during an outage: when Ben only reads, it brings no messages but Ben's bookmarks at read; when Ben replies, it brings his reply and his bookmarks at the reply's number.
  - The app's re-check logic itself has no automated test: the project has no frontend test runner, and adding one would be a new library. It was checked by hand.
- Checked by hand: Redis stopped, Ana sends, Ben sees it within a minute, opens it and goes back: no badge, still none after a reload. Still during the outage, Ana's tick turns teal within a minute, and Ben's reply reaches her within a minute. Redis started: everything is live again. With Redis up: grey ticks, teal ticks and "typing..." as before.

**New ideas**
- Two doors, one room: the live line and HTTP both lead to the same `save_bookmark`. The rules live in one place, so the two doors can never drift apart.
- The truth must not depend on a helper: `read_up_to` lives in PostgreSQL, but the only way to move it used to go through Redis (ticket, live line). A Redis outage could then leave the truth wrong. The HTTP door removes that dependency.
- Save first, push second: the receipt is pushed only after the commit, so nobody hears about a bookmark that isn't saved.
- Idempotent: sending the same "read #42" twice changes nothing the second time, and pushes nothing. That's what makes it safe for the app to resend after a drop.
- Confirmed vs wanted: the app tracks the highest number it wants the server to have, and the highest the server has confirmed. Only the gap is sent, so a reconnect or a retry doesn't flood the server.
- Known down vs not yet up: while the line is first connecting, the app waits; only once it has dropped or failed does it take the HTTP door. That avoids one HTTP request per chat on every page load.
- A badge from two numbers: the server's read bookmark can lag behind the screen for a moment, so the badge uses the higher of the two.
- Push vs pull: a push is the server calling the app (the live line, needs Redis). A pull is the app asking the server (plain HTTP, needs only PostgreSQL). When pushes stop, a slow pull every 60 s keeps the screen roughly right, and it stops once pushes are back.
- One request for two reasons: two triggers ("a newer message" and "the line is down") share one check at the same moment, so they can't double up.

**In my words** (Adithya writes this)
- Why the read bookmark gets an HTTP door but typing doesn't: "Read" is permanent state. If the server doesn't know Ben read a message, his unread badges will pop back up, and Ana's ticks will stay grey instead of turning teal. It must be saved, so it gets an HTTP fallback. "Typing" is just a temporary animation that only matters for 3 seconds. If the live line is down, and typing takes 60 seconds to reach the server via HTTP, the person has already finished typing and sent the message. It's pointless, so we don't bother.

### Task 23: Notification worker with retries and a failed-jobs queue (RabbitMQ)
**What was built**
- `docker-compose.yml`: RabbitMQ (`rabbitmq:4.3.7-management`, D25). Port 5672 for programs, 15672 for the web page. Its user and password come from `.env` (the built-in `guest` only works inside the container). A named volume and a fixed hostname, so parked jobs survive `docker compose down`. The health check is `check_port_connectivity`: "healthy" means the port really takes connections, not just that RabbitMQ is booting.
- `.env.example`: `RABBITMQ_USER`, `RABBITMQ_PASSWORD`, `RABBITMQ_URL` (vhost `/`, written `%2F`) and `TEST_RABBITMQ_URL` (vhost `parley_test`), plus the two one-time commands that make the test vhost.
- `backend/requirements.txt`: `pika==1.4.4`.
- `backend/app/config.py`: `rabbitmq_url`, `notify_wait_ms` (5 s), `notify_retry_ms` (10 s, 1 min, 5 min) and `notify_fake_fail_times` (0). In milliseconds, so tests can use a few hundred.
- `backend/app/notify/queues.py` (new), every box in one place:
  - `NOTIFY` (the worker reads only this), `WAIT`, `RETRIES` (`.10s`, `.1m`, `.5m`), `FAILED`.
  - `declare(channel)`: makes every box, durable. The wait and retry boxes each get a timer (`x-message-ttl`) and a dead-letter route back into `notify`. Declaring a box that's already there with the same settings does nothing; a different timer is refused (error 406).
  - `connect(url)`: one try, at most 1 s to reach RabbitMQ and 2 s to log in.
  - `send_job(channel, box, body, headers)`: puts one persistent job in a box. With confirms on, it waits for RabbitMQ's "got it". The publisher, the worker and replay all use it.
- `backend/app/notify/publisher.py` (new), the backend's side:
  - `publish(message, recipient_ids)`: one job per recipient into `notify.wait`, `{message_id, chat_id, seq, recipient_id}`, header `attempt: 1`. Never the text (D12). Never raises.
  - One shared connection behind a lock, because pika isn't thread-safe and sync routes run on many threads. A send waits at most 1 s for the lock, or that notification is lost.
  - A connection that went stale (RabbitMQ restarted, or it closed an idle one) gets one fresh try.
  - The boxes are declared on every new connection, so the backend starts and chats fine with RabbitMQ down, and the boxes appear as soon as it's back.
  - After a failed connect, `_skip_until` skips publishing for 10 s and logs "RabbitMQ is down" once, so an outage adds 1 s to one send, not to every send. Only "can't connect" counts as down; any other error (like a 406) is logged with its real reason.
  - `reset()`: forgets the connection and the skip, for tests.
- `backend/app/messages/routes.py`: after a new message is saved and pushed, `notify.publish()` for every member except the sender. A resend (200) publishes nothing.
- `backend/app/notify/notifier.py` (new):
  - `LogNotifier.send(user_id, user_name, title)`: logs "notify Ben: New message from Ana". T24 swaps in real browser push with the same `send()`.
  - `fake_fail(attempt)`: with `NOTIFY_FAKE_FAIL_TIMES=N`, tries 1 to N fail on purpose (`NotifyFailed`).
- `backend/app/notify/worker.py` (new), run as `python -m app.notify.worker`:
  - `parse(body)`: reads a job. Bad JSON, a missing field or a bad id raises `BrokenJob`.
  - `handle(job, attempt)`: one query for the recipient's `read_up_to` and name, one for the sender's name. Message or member gone: skip. `read_up_to >= seq`: "skip: already read". Redis `notified:<message>:<user>` there: "skip: already notified". Otherwise `fake_fail`, then the notifier, then the Redis note with a 24 h timer. If the note can't be written after a send, it only logs a warning: retrying would notify again.
  - `on_job(...)`: a broken job goes straight to `notify.failed`. Any other failure (the notifier, PostgreSQL, Redis) goes to the next retry box with `attempt + 1`, or to `notify.failed` with `last_error` after try 4. The ack always comes last, after RabbitMQ confirmed the new copy.
  - `open_channel()` (confirms, declare, prefetch 10), `consume(channel, should_stop)` (wakes up every second to check whether to stop; tests use it too), `serve()` (reconnects with 1, 2, 4 ... 30 s waits), `main()` (Ctrl+C stops it; closing the connection hands any unacked job back). pika's own tracebacks are silenced; the worker logs one line per event instead.
- `backend/app/notify/replay.py` (new), run as `python -m app.notify.replay`: counts what's parked right now and moves exactly that many from `notify.failed` to `notify` with attempt 1, acking each one only after the new copy is confirmed. The count stops a broken job (which parks itself again at once) from going round and round.
- `backend/tests/conftest.py`: reads `TEST_RABBITMQ_URL` and refuses any vhost but `parley_test`. The app gets a 1 s wait, retries of 0.1, 0.2 and 0.3 s, and fake fails forced to 0. Each run deletes and remakes the test boxes (so changed timers never hit a 406). After each test every box is emptied and the publisher reset. A new `rabbit` fixture gives a channel with confirms on.
- Tests (98 in all):
  - `test_notify_publish.py` (new): a send puts one job for Ben (none for Ana, none for a resend) in `notify.wait`, with no text. RabbitMQ down: the send gives 201 and is saved. Two quick sends while down: only the first tries to connect, and the warning is logged once.
  - `test_notify_worker.py` (new): sent and noted in Redis; skipped when Ben read it through the HTTP door; a job that runs twice notifies once; fake fails at 2: sent on try 3; at 10: parked after try 4 with `last_error`; broken jobs (not JSON, missing fields) parked at once with no retry; replay moves a parked job back and it's sent; a worker stopped mid-job (before its ack): a new worker gets the same job and sends it.
- `.github/workflows/ci.yml`: a RabbitMQ service that makes `parley_test` at start (`RABBITMQ_DEFAULT_VHOST`), and the two URLs.
- Checked by hand:
  - Ben's tab closed: about 5 s after Ana's send, the worker logs "notify Ben Ortiz: New message from Ana Lima". Ben's window focused within 5 s: "skip: already read" (a split-screen window that isn't focused doesn't count as read, D20).
  - Worker stopped, 3 messages sent, worker started: all 3 sent.
  - `NOTIFY_FAKE_FAIL_TIMES=2`: try 1 failed at 00:06:47, try 2 failed at 00:06:57, try 3 sent at 00:07:57.
  - `NOTIFY_FAKE_FAIL_TIMES=10`: tries at 00:08:35, 00:08:45, 00:09:45 and 00:14:45, then parked in `notify.failed` with `attempt: 4` and `last_error`. With a normal worker, replay printed "Moved 1 jobs" and the job was sent as try 1.
  - RabbitMQ stopped, 3 quick sends: all 201 and saved; the first took 1.15 s (one connect try), the next two 0.05 s (skipping). Started again: the next send put its job in `notify.wait` with no warning.
  - RabbitMQ restarted under a running worker: "Lost RabbitMQ", then 1, 2, 4, 8 s, then "Worker ready". Under the backend: the next send went through on a fresh connection, and a persistent job survived the restart.

**New ideas**
- Message queue: a post office between programs. The backend drops a job and moves on; the worker picks it up when it can. If the worker is off, jobs wait instead of being lost.
- Queue (box), durable, persistent: a durable box survives a RabbitMQ restart; a persistent job inside it is written to disk, so it survives too. You need both.
- Ack: the worker's "done, delete it". Until then the job is only lent out (Unacked). If the worker's connection dies, RabbitMQ puts it back.
- At least once: acking last means a job is never lost, but can run twice (a crash after sending, before the ack). The Redis note `notified:<message>:<user>` makes the second run do nothing. That's called making the job idempotent.
- Publisher confirms: RabbitMQ's "got it" for each job the backend sends. Without it, a job could vanish on the way and nobody would know.
- Prefetch: how many unacked jobs RabbitMQ lends the worker at once (10), so it isn't flooded and several workers could share the work.
- TTL and dead-lettering: a box's timer (`x-message-ttl`). When it runs out, the job is "dead-lettered": sent on to another box (`notify`). That's how a job waits 10 s, 1 min or 5 min with no code sleeping.
- One timer per box, not per job: RabbitMQ only checks the job at the front of a box. Mixing 5 min and 10 s jobs in one box would make the 10 s ones wait behind the 5 min one.
- Default exchange: the built-in exchange `""` delivers a job straight to the box with the same name as its routing key.
- Vhost: a separate set of boxes inside one RabbitMQ, like Redis's numbered databases. Dev uses `/`, tests use `parley_test`.
- Parked jobs (a dead-letter queue) and replay: jobs that kept failing wait in `notify.failed` with their last error, instead of being retried forever or lost. Once the cause is fixed, replay sends them all back.
- Broken vs failing: a job with bad JSON will never work, so retrying only wastes time; a job whose notifier is down may work later, so it's retried.
- A small circuit breaker: after RabbitMQ refuses once, stop trying for 10 s. Fast failure for everyone instead of a 1 s wait on every send.
- Thread safety: pika's connection can only be used by one thread at a time; a lock makes the others take turns.
- The outbox pattern (not built yet, D25): today a job is lost if RabbitMQ is down at the moment of a send. Writing the job into PostgreSQL in the same transaction as the message, and sending it from there later, would close that gap.

**In my words** (Adithya writes this)
- How a job waits 10 s, 1 min or 5 min with no sleeping code: We use RabbitMQ's built-in timers (TTL and dead-lettering) instead of writing code that sleeps. We create separate holding boxes (queues) for each wait time. When a job fails, we drop it into the box for its next wait. The job sits there doing nothing until the timer on that box hits zero. At that exact moment, RabbitMQ automatically picks the job up and routes it back to the main worker queue. We use separate boxes for each time so a job waiting 5 minutes doesn't block a job waiting 10 seconds.

- Why the worker acks only at the end, why that means a job can run twice, and how "already notified" stops a double: If the worker told RabbitMQ it was "done" before sending the notification, a crash would mean the notification is lost forever. By acking only after the notification is sent, RabbitMQ ensures the job is never lost—if the worker crashes, RabbitMQ just gives the job to someone else. But this means if it crashes right after sending but before acking, the job runs twice. To stop a double notification, the worker saves a "notified" note in Redis. If it runs again, it sees the note and skips the send.

- What `notify.failed` and replay are for, and why a broken job skips the retries: `notify.failed` is a parking lot for jobs that failed all their retries. Instead of losing them or retrying forever, we save them there with their final error. Replay is a command we can run later to take all those parked jobs and put them back in the queue once we fix the bug. However, if a job has bad data (like a missing field or invalid JSON), it is physically impossible to ever succeed. So we skip the wait and send it straight to the parking lot to save time.

### Task 24: Real browser notifications (Web Push)
**What was built**
- `backend/requirements.txt`: `pywebpush==2.5.0` (latest stable on PyPI). The helpers it installs (requests, aiohttp, py-vapid, http-ece) count as part of it (D26).
- `.env.example`: `NOTIFIER=webpush`, placeholders for `VAPID_PRIVATE_KEY`, `VAPID_PUBLIC_KEY` and `VAPID_SUBJECT` (a `mailto:`), and the one-line command that makes the key pair. `REDIS_URL` and `TEST_REDIS_URL` now use `127.0.0.1` (D22).
- `backend/app/config.py`: `notifier` (`log` or `webpush`, `log` by default) and the three VAPID settings, empty by default, so CI needs no keys.
- `backend/app/push/models.py` (new) and a migration: `push_subscriptions` with `id`, `user_id` (indexed, deleted with the user), `endpoint` (unique), `p256dh`, `auth`, `created_at`. One row per browser, owned by whoever subscribed on it last. Written by hand (Docker was off) and confirmed with `alembic check`.
- `backend/app/push/schemas.py` (new): `SubscribeIn` is exactly what the browser's `subscription.toJSON()` gives. The endpoint must start with `https://` (max 2048), so the worker never POSTs to something like `http://127.0.0.1` on our own machine.
- `backend/app/push/routes.py` (new):
  - `GET /api/push/key`: the public key, or 503 if `.env` has none.
  - `POST /api/push/subscribe`: one upsert (`INSERT ... ON CONFLICT (endpoint) DO UPDATE`): a new browser is added; a known one moves to the current user with its current keys. Two tabs at once still make one row. 10 per minute per user (`limits.PUSH_SUBSCRIBE`).
  - `DELETE /api/push/subscribe` with `{endpoint}`: deletes only my own row. Someone else's gets the same 204, so the reply doesn't say whose browser it is.
- `backend/app/notify/queues.py`: `Job` moved here from the worker, because the notifier now needs it and the worker imports the notifier (two files importing each other is a circle).
- `backend/app/notify/notifier.py`, the new shape `send(job, user_name, title)` returning what happened (D25):
  - `LogNotifier`: one log line and one note per person (`notified:<message>:<user>`), as in T23.
  - `WebPushNotifier`: loads the user's devices; none → "skip: no devices". For each device without a note `notified:<message>:<device>`: lock the payload `{"title", "chat_id"}` with that browser's keys, sign it with our VAPID key, POST it (TTL 1 hour, 10 s time limit). 201 → write that device's note. 404/410 → delete the row, no retry. Anything else (429, 5xx, other 4xx like a wrong key, a timeout, can't connect) → keep going with the other devices, then raise `NotifyFailed` so T23 retries, and the noted devices are skipped next time.
  - A fresh VAPID claims dict for every push: pywebpush writes the push service's address into it, and a reused one would be wrong for a device on another push service.
  - `make_notifier()`: the `NOTIFIER` setting picks one. `webpush` without keys refuses to start.
- `backend/app/notify/worker.py`: hands the job to the notifier and logs its answer. It no longer touches the notes. The start line says which notifier it uses.
- `frontend/public/sw.js` (new), the service worker: on a push, closes the chat's old notification and shows a new one with `tag = chat_id`, so there's one per chat and every new message still pops up. A click focuses an open Parley tab, or opens one. `skipWaiting()` lets a new version of the file take over at once.
- `frontend/src/lib/push.ts` (new): `pushState()`, `turnOnPush()` (only on the click: permission, public key, register `sw.js`, subscribe, POST), `resendPush()` (after log-in, only a subscription the browser already has), `turnOffPush()` (DELETE first while the access token still works, then unsubscribe in the browser).
- `frontend/src/features/auth/AuthProvider.tsx`: re-sends after log-in and after a page load; log-out turns push off first. Push problems never hold up logging in or out.
- `frontend/src/features/chat/ChatColumn.tsx`: the gear menu has "Turn on notifications" / "Notifications on" / "Notifications blocked", hidden where pushes can't work. If turning on fails, the reason shows in red under it.
- Tests (126 in all):
  - `tests/conftest.py`: `push_subscriptions` in the TRUNCATE; `NOTIFIER=log` forced, so no test ever pushes for real.
  - `test_push_routes.py` (new): the key (and 503 without one); subscribe saves; twice from one browser = one row; subscribe moves a browser to the new user; unsubscribe deletes my own row but not someone else's; http addresses refused; log-in needed; the 11th subscribe in a minute gets 429.
  - `test_notify_webpush.py` (new), with a fake push service and pretend browsers that have real keys: 201 sends and notes that device; the same job again is not pushed twice; the push, opened with the browser's own key, is exactly the title and chat id, with a TTL of 3600 and a VAPID signature; 404/410 delete the device with no retry; 500, 503, 429, 403, 400, a timeout and can't-connect all raise `NotifyFailed` and keep the device; no devices is skipped; two devices with one 500: the retry only tries the failed one; one device gone, the other still gets it; the setting picks the notifier; webpush without keys refuses to start; and the whole way through the worker: Ana sends "meet me at 6", Edge gets it once, Firefox fails twice and gets it on try 3, and no push contains the text.
  - `test_notify_worker.py`: updated for the new `send()` shape.
- Checked by hand (Ben on Edge, Microsoft's push service):
  - The first click gave "Registration failed - push service error": the browser couldn't get an address from its push service. The second try worked.
  - Ben's tab closed: about 5 s after Ana's send, Windows showed "New message from Ana Lima" with no text, and clicking it opened Parley.
  - 3 quick messages: 3 pushes sent, one notification on screen (same tag).
  - Ben's chat open in front: "skip: already read", no notification.
  - Ben logged out: his row was deleted, and the next message gave "skip: no devices".
  - A notification that didn't pop up (#238): the worker said "sent", but Windows' list (Win + N) still held an older one with the same tag, and a replacement is silent by default. `renotify: true` alone didn't fix it in Edge (#240, #241: one pop-up). Closing the old notification first and showing a new one did: #242 and #243, 10 s apart, gave two pop-ups and one entry in the list. Edge's DevTools (Application → Service workers) showed which `sw.js` was running.
  - A worker signed with a wrong VAPID key: Microsoft answered 401 (not 403) on every try. Tries at 02:39:55, 02:40:05, 02:41:06 and 02:46:07, then parked in `notify.failed`. With the real key back, replay printed "Moved 1 jobs" and the worker gave "skip: already read", because Ben had opened the chat in the meantime: the replayed job checks again before pushing.

**New ideas**
- Web Push: a server can't reach a closed tab, but the browser keeps one line open to its own push service (Google's for Chrome, Microsoft's for Edge, Mozilla's for Firefox). We hand the push service a box addressed to Ben's browser, and the browser wakes up a small script to open it.
- Service worker: a small script the browser keeps registered for a site, even when no tab of that site is open. It can wake up for a push and show a notification.
- Push subscription: what the browser gets from its push service when it says yes. An endpoint (the browser's own address there) and two keys (`p256dh`, `auth`).
- End-to-end locked payload: the push is encrypted with the browser's keys, so the push service passes it along but can't read it. Only that browser can open it.
- VAPID: our own key pair. The browser subscribes with our public key, and we sign each push with the private one, so the push service only accepts pushes for Ben's browser from us.
- Upsert: one statement that says "insert this row, or if the unique value is already there, update that row instead". No race between "is it there?" and "add it".
- Notification tag: notifications with the same tag replace each other, so one chat shows one notification however many messages arrive. But a replacement is silent, so the service worker closes the old one and shows a fresh one, which pops up.
- Service worker updates: a changed `sw.js` normally waits until every tab using the old one has closed. `skipWaiting()` makes it take over at once.
- Final vs temporary errors: 404/410 means the browser is gone for good, so retrying is pointless and the row is deleted. 5xx, 429 or a timeout may work later, so they retry.
- Per-device "already sent" notes: when one device works and another fails, the retry only tries the failed one, so nobody gets the same notification twice.
- TTL on a push: how long the push service keeps trying to deliver it. A notification an hour late is useless, so it's dropped after one hour.
- Asking for permission only on a click: browsers punish sites that ask on page load (quiet prompts, or auto-blocking).

**In my words** (Adithya writes this)
- How Parley reaches Ben's browser when his tab is closed (push service plus service worker): A website can't talk directly to a closed browser. Instead, the browser connects to a third-party push service (like Microsoft for Edge or Google for Chrome) and gets a unique web address. Parley sends an encrypted message to that address. The push service wakes up the closed browser in the background, and a tiny background script (the Service Worker) wakes up to display the notification.

- Why a 410 deletes the device but a 500 retries: A 410 Gone means the browser is permanently gone (uninstalled, or browser data cleared). It is dead, so retrying is a waste of time and we delete the device from our database. A 500 (or a 429 or a timeout) means the push service is temporarily broken or overwhelmed. If we wait and retry, it will likely succeed later.

- Why the "already sent" note is per device, not per person: Because Ben might have a phone, a tablet, and a laptop. If his phone receives the push but his tablet fails, we only want to retry the tablet. If the note was per person, a retry would either skip the tablet entirely or double-notify the phone. Tracking it per device ensures every browser gets exactly one notification.

### Task 25: Every part in a container (Dockerfiles + Docker Compose)
**What was built**
- Base images, each an exact tag checked on Docker Hub (D27's version rule: patches are taken at once): `python:3.13.17-slim-trixie`, `node:24.22.1-alpine` (Node 24 is the LTS line CI uses; 24.22.1 is a security patch), `nginx:1.30.6-alpine` (the stable line; 1.30.6 fixes four CVEs), and `postgres:17.11` (the newest 17.x; the local database already ran 17.11, so its data didn't change).
- `backend/.dockerignore` (new): `.env`, `.venv/` and the caches never go into the image.
- `backend/Dockerfile` (new): one image for backend, worker and migrate. `requirements.txt` is copied and installed before the code, so a code change reuses the packages layer (`pip install` showed `CACHED`). Runs as the normal user `parley`. The default command is uvicorn with `--proxy-headers --forwarded-allow-ips "*"`, written as a list so uvicorn itself is PID 1 and gets `docker stop`'s signal. 358 MB.
- `backend/app/notify/worker.py`: one line in `main()`, `signal.signal(signal.SIGTERM, signal.default_int_handler)`. In a container the worker is PID 1, and Linux ignores SIGTERM for PID 1 unless the program handles it. Now SIGTERM raises `KeyboardInterrupt`, so it takes the same path as Ctrl+C: the job in progress isn't acked, closing the connection hands it back to RabbitMQ, then "Stopped." (that path was already tested in T23).
- `frontend/.dockerignore` (new): `node_modules/`, `dist/` and `.env` stay out; the image runs its own `npm ci` and build.
- `frontend/Dockerfile` (new), two stages: Node runs `npm ci` and `npm run build`; then only Nginx and `dist/` are kept. Runs as the `nginx` user (it owns its pid file and cache folder). 93 MB.
- `frontend/nginx.conf` (new), replaces Nginx's default site, listens on 8080:
  - `try_files $uri $uri/ /index.html`: an address that isn't a file gets the app, so `/login` works after a reload.
  - `sw.js` gets `Cache-Control: no-cache`.
  - `/api/` goes to `backend:8000` with the WebSocket upgrade headers and `proxy_read_timeout 60s` (the app pings every 25 s).
  - `X-Forwarded-For $remote_addr`: overwritten, never added to.
  - `resolver 127.0.0.11 valid=10s` and the address in a variable: Nginx looks `backend` up again every 10 s instead of only at start (see the 502 below).
- `docker-compose.yml`:
  - `x-parley-backend` holds what backend, worker and migrate share (build, image, `app` profile, `env_file: .env`, and the three addresses built from the `POSTGRES_*` and `RABBITMQ_*` values with the service names `db`, `redis`, `rabbitmq`).
  - `migrate` (`alembic upgrade head`) waits for db, Redis and RabbitMQ to be healthy. `backend` and `worker` also wait for migrate to finish OK (`service_completed_successfully`). `web` waits for the backend to be healthy.
  - Backend health check: Python's `urllib` asks `/api/health` (slim has no curl). The backend has no `ports:`, so only Parley's network reaches 8000. `web` is the only new port: 8080.
  - `stop_grace_period`: 10 s for the backend, 15 s for the worker.
  - `docker compose up` alone still starts only db, Redis and RabbitMQ.
- `.github/workflows/ci.yml`: a new `containers` job. It makes a throwaway `.env` from `.env.example` (with `NOTIFIER=log`, since the example's VAPID keys are fake), builds both images, runs `docker compose --profile app up -d --wait`, asks `http://localhost:8080/api/health` through Nginx, shows the logs if anything failed, and always shuts down. The test jobs are unchanged.
- `.env` (not committed): the RabbitMQ password had an `@`, which would break the `amqp://` address Compose builds. Changed to 32 letters and numbers with `rabbitmqctl change_password` (the user already lived in the volume, so `.env` alone wasn't enough) and written into the three RabbitMQ lines.
- Checked (the long ones by running them, the screens by hand at http://localhost:8080):
  - `docker compose --profile app up --build`: migrate `Exited (0)`; db, Redis, RabbitMQ and the backend `healthy`; worker and web `Up` (they have no health check).
  - `.env` isn't in either image: `find / -name .env` inside both printed nothing.
  - Ana25 (Chrome) and Ben25 (Edge) signed up, chatted live, got two ticks, then blue ticks, and saw "typing...". Reloading on `/login` showed the app, not a 404.
  - Ben turned notifications on again (8080 is a different site from 5173), minimized Edge, and got "New message from Ana25". `docker compose logs worker`: `#1 ... skip: no devices`, then `#2 ... sent`.
  - `docker compose restart backend`: back in 3 s, both apps reconnected by themselves (too fast to see "Reconnecting..."). Then the backend stopped for 30 s: both apps showed "Reconnecting...", Ana's "sent while down" waited, then went out (401, refresh, 201) and reached Ben. Nothing lost.
  - `docker compose stop worker`: 2 s, "Stopped. Unfinished jobs went back to RabbitMQ."
  - Real IP: the backend logged `172.20.0.1` (Docker's gateway, where the browser's requests come from), never Nginx's `172.20.0.7`. A request with a fake `X-Forwarded-For: 6.6.6.6` still showed `172.20.0.1`.
  - A 502 found by `up --wait`: it made a new backend container with a new address (`.6` → `.5`), and Nginx still used the old one, since it had looked `backend` up only at start. After the resolver fix, the backend was moved to a new address (`.5` → `.8`) and Nginx found it within about 1 s without a restart.
  - Laptop uvicorn (8000) and Vite (5173) worked at the same time as the containers (8080). All 126 tests pass.

**New ideas**
- Image vs container: an image is a frozen box (Linux, Python, the code, the packages). A container is one running copy of it. Parley's one backend image runs as three containers: backend, worker and migrate.
- Layers and their cache: each line of a Dockerfile saves a layer. Docker reuses a layer until what it depends on changes, so installing packages before copying the code means a code change doesn't reinstall them.
- `.dockerignore`: what never goes into the image. Secrets come in at run time instead, from Compose's `env_file`.
- Multi-stage build: a big stage builds (Node and `node_modules`), and a small final stage keeps only the result (Nginx and `dist`).
- Service names as addresses: inside Compose's network, `db`, `redis`, `rabbitmq` and `backend` work like hostnames. `127.0.0.1` inside a container means that container itself.
- Health checks and start order: `depends_on` with `service_healthy` waits until a small test passes; `service_completed_successfully` waits for a one-shot container to exit 0.
- One-shot migrate container: migrations run once, before any backend copy starts, so two copies never change the tables at the same time.
- Profiles: services marked `app` start only with `--profile app`, so plain `docker compose up` stays the dev helpers.
- Signals and PID 1: `docker stop` sends SIGTERM, waits the grace period, then kills hard. Linux ignores SIGTERM for PID 1 unless the program handles it, so the worker handles it itself.
- Reverse proxy: Nginx sits in front, hands out the app's files and passes `/api` and the live line on to the backend. That's the same job Vite's proxy does in dev.
- `X-Forwarded-For`: the header that tells the backend who really asked. Nginx overwrites it with the address it actually saw, so a client's own fake value is thrown away. Trusting it is safe only because nothing outside Parley's network can reach the backend directly.
- Docker's name service (`127.0.0.11`): a new container can get a new address. Nginx must look the name up again, not keep the one it found at start.

**In my words** (Adithya writes this)
- What the difference is between an image and a container: An image is a frozen, read-only blueprint of the application (containing the OS, the code, and the packages). A container is the actual running, live instance of that blueprint. You can spin up many containers from a single image.

- Why migrations run in their own one-shot container instead of inside each backend copy: If multiple backend copies start at the same time and each tries to alter the database tables, they will collide and crash. By using a dedicated one-shot container, Compose ensures the migrations run exactly once. The backend copies are told to wait until the migration container finishes successfully before they start up.

- How Nginx lets the backend see the real IP, and why a client can't fake it: A client can easily send a fake "X-Forwarded-For" header pretending to be a different IP. Nginx sits in front and sees the actual connection IP, then completely overwrites that header with the truth before passing it to the backend. The client cannot fake it because the backend has no public port open to the internet; the only way to reach the backend is through Nginx.

### Task 26: Two backend copies behind Nginx, and a failover demo
**What was built**
- `docker-compose.yml`: `backend` became `backend_a` and `backend_b`. A new `x-parley-copy` block holds what they share (the T25 block, the waits, the health check, the 10 s stop grace). They differ only in `COPY_NAME`. The three addresses got their own name (`&parley-env`), because `<<:` only pastes one level deep: a copy that set just `COPY_NAME` would have lost `DATABASE_URL`, `REDIS_URL` and `RABBITMQ_URL`. Checked with `docker compose config`. `migrate` still runs once, first. `web` waits for both copies to be healthy.
- `frontend/nginx.conf`: an `upstream backends` with both copies, `zone backends 64k`, `least_conn`, and `resolve max_fails=1 fail_timeout=10s` on each server. `resolver 127.0.0.11 valid=10s` moved up to the top of the file. In `/api/`: `proxy_pass http://backends`, `proxy_connect_timeout 2s`, `proxy_next_upstream error timeout` (no `non_idempotent`). This replaces T25's `set $backend` trick.
- `resolve` checked first in our exact image, `nginx:1.30.6-alpine` (free Nginx has had it since 1.27.3). With names that didn't exist yet, `nginx -t` said "test is successful". The same file without `resolve` failed: `host not found in upstream "backend_a:8000"`.
- Clean stop: no new code. uvicorn 0.54.0 already does it. On SIGTERM it stops taking new connections and sends close code 1012 ("server restarting") to every open live line (`server.py` and `websockets_sansio_impl.py`). A comment in `live/routes.py` says so.
- `backend/app/live/routes.py`: `hello` carries `"copy": settings.copy_name`. `frontend/src/lib/live.ts` logs `live line on copy B` in the console. `types.ts` knows the new field. Nothing new on screen.
- `backend/app/config.py`: `cookie_secure: bool = False`. `auth/routes.py` uses it both when setting the refresh cookie and when deleting it at log-out, because a delete must match how the cookie was made.
- Tests: `test_live.py`'s hello test expects `copy`. New `test_cookie_secure_adds_the_secure_flag_when_set_and_deleted`: no `Secure` by default; with the setting on, log-in and log-out both carry it. All 127 tests pass.
- `.github/workflows/ci.yml`: the test job's Postgres is pinned to `postgres:17.11`. The containers job asks `/api/health` through Nginx 10 times and fails unless both A and B answer (tried here first with `bash -e`).
- Checked (by script through :8080, with throwaway accounts `t26-ana` and `t26-ben`):
  - 10 × health: `A, B, A, B, A, B, A, B, A, B`.
  - 25 quick sends: 20 × 201 then 5 × 429. A served 13 (10 ok, 3 limited), B served 12 (10 ok, 2 limited). One count, shared in Redis.
  - Ana's line on A, Ben's on B, stop A: Ana's line closed 0.65 s later with code 1012 and was back on B 1.68 s after the stop. A send during it, sent twice with the same `client_msg_id`, reached Ben once (#21). Ben's line never dropped. 33 health checks during it: 0 errors, all B from 1 s after the stop.
  - uvicorn itself took 0.12 s from "Shutting down" to "Finished". `docker compose stop` took 4.75 s, which is Docker Desktop's own overhead.
  - Start A again: A answered again 8.3 s after `docker compose start` (5.2 s of that was Docker), 0 errors.
- Checked by hand (Ana in Chrome, Ben in Edge, at :8080): Ana on B, Ben on A, chatting with ticks. `docker compose stop backend_b` mid-chat: the "available" pill turned into "Reconnecting..." with a grey dot for about 2 s, the console added `live line on copy A`, the message sent during it arrived once, and Ben noticed nothing. `docker compose start backend_b`: a new line landed on B again.
- Found along the way:
  - `least_conn` sends every short request to the copy with fewer open live lines. With 2 lines on A and 1 on B, 10 health checks all went to B. CI has no open lines, so there it takes turns.
  - When a container stops, Docker's name service answers "Server failure", not "no such name", so Nginx keeps the old address to be safe. While a copy stays down, about one request every 10 s waits the 2 s connect timeout, then goes to the other copy. No errors. Seen in the second demo run: Ana's ticket POST went to B's old address, timed out after 2 s, then went to A. That's a POST that never reached a copy, so it's safe to send on.
  - Renaming `backend` left the old `parley-backend-1` container running, because `down` only removes services still in the file. Removed by hand (`up --remove-orphans` also does it).

**New ideas**
- Load balancer: one front door (Nginx) spreading requests over several copies of the same app. The `upstream` is its list of copies.
- `least_conn`: the next request goes to the copy with the fewest open connections. It fits live lines that stay open for hours better than taking turns does.
- Passive health checks: Nginx doesn't ping the copies. It notices a failure on a real request (`max_fails=1`), skips that copy for `fail_timeout=10s`, then tries it again.
- Retrying on the next copy (`proxy_next_upstream`): a GET can always be repeated. A POST is only sent on if it never reached the first copy.
- Stateless copies, no sticky sessions: a copy keeps nothing about a user that the other copy needs. Tickets, pushes, presence and limits are in Redis, data in PostgreSQL. So any request or live line can go to either copy, and losing a copy loses no data.
- Graceful shutdown: on SIGTERM a server stops taking new work and closes what's open with a clear reason (1012), so clients move on at once instead of waiting for a timeout.
- `resolve` in an upstream: Nginx keeps looking names up while it runs, and starts even if a copy is missing.
- The `Secure` cookie flag: the browser sends the cookie over HTTPS only. A cookie must be deleted with the same settings it was set with.

**In my words** (Adithya writes this)
- Why Parley doesn't need sticky sessions: "Sticky sessions" means locking a user to one specific server forever. Parley doesn't need this because the servers don't hoard any secrets in their own memory. Tickets, online status, and spam limits are stored in Redis. Messages are in PostgreSQL. Because both servers share the exact same brain, any request can go to any server, and you can lose a server without losing any data.

- What Nginx does when a copy dies: Nginx acts as the load balancer. If it tries to send a request to Copy A and Copy A doesn't answer, Nginx immediately stops sending traffic to A for 10 seconds and sends everything to Copy B instead. It routes around the dead server automatically.

- Why Nginx doesn't retry a POST, and why our sends are safe anyway: Nginx won't automatically retry a POST because if the first server actually saved it before crashing, retrying would save it twice. However, Parley is safe anyway because we use a client_msg_id. If Nginx retries it and the second server tries to save it, the database sees the duplicate ID, refuses to save it again, and just hands back the first copy.

- Why the rate limit still works across two copies: Because the counter lives in Redis, not in the server's memory. If you send 10 messages to Copy A, Copy A adds 10 to the Redis counter. If you send 10 more to Copy B, Copy B adds 10 to that same Redis counter. The total is 20, and the limit triggers, no matter which server you talk to.

---

### Task 27: Responsive layout fix
**What was built**
- `frontend/src/features/chat/ChatScreen.tsx`: two pieces of state decide what shows.
  - `panelOpen`: from 1280 px, the side panel is open or folded to a thin strip.
  - `narrowView`: below 1280 px, which part has the shared spot: `"list"`, `"chat"` or `"panel"`. Phones show only that part. At 768-1279 px the list always shows, and `"panel"` takes the chat's place.
- `frontend/src/features/chat/types.ts`: the `NarrowView` type, shared by ChatScreen and Conversation.
- `frontend/src/features/chat/Conversation.tsx`:
  - Never narrower than 360 px from 768 px up (`md:min-w-90`). It hides only when the side panel takes its place.
  - Tapping the name opens the side panel below 1280 px (hand cursor there). The "Messages"/"Participants" tabs are gone.
  - A file dropped on the chat does nothing (`dropEffect = "none"` gives the "not allowed" cursor), instead of opening in the tab and leaving Parley.
  - When the chat comes back into view, it scrolls to the newest message and checks "read" again.
- `frontend/src/features/chat/SidePanel.tsx`: one panel, three shapes: a phone screen, the chat's spot at 768-1279 px, or its own column from 1280 px that folds to a strip (open button and avatar only). The back arrow sits in the top-left corner of the profile block. A 1:1 chat shows "online" or "last seen", and every chat shows "No files yet".
- `frontend/src/features/chat/ChatColumn.tsx`: no phone header. 280 px wide at 768-1023 px, 340 px from 1024 px. No "available" pill: "Reconnecting..." shows under the name only while the live line is down. No "..." menu.
- `frontend/src/features/chat/IconRail.tsx`: only from 768 px. The logo, a Chats marker (not a button, since there's nothing to click) and my avatar.
- `frontend/src/features/chat/MessageBox.tsx`: just the text box and the send button. Tighter on phones; a hint that doesn't fit ends in "...".
- `frontend/src/features/chat/MessageBubble.tsx`: bubbles at most 75% wide.
- `frontend/src/features/chat/NewChatBox.tsx`: never wider than the screen.
- Deleted: `frontend/src/data/fake.ts` (the fake file numbers) and `frontend/src/features/chat/UploadView.tsx` (comes back from Git with files in v2).
- `docs/design/screens.md`: a "Window sizes" section, and every screen note matches D8.

**Why**
- On laptops, all four columns tried to fit side by side. The chat got crushed to one letter per line, and the header and send button piled on top of other parts.
- The fake file numbers looked real on real chats.
- A button that does nothing looks broken to someone trying the app. Each hidden button comes back only in the task that makes it work (D8). Dashboard, Tasks and Stats came from the reference design, not WhatsApp, so they're gone for good.
- Recruiters will open the live link on their phones (T28).

**How the layout got here**
- Try 1, the brief's drawer: the panel slid over the chat with a grey overlay. It looked worse.
- Try 2: opening the panel closed the chat list. But on a big screen, everything should show.
- Try 3, kept: all four columns from 1280 px. Below that, the panel swaps places with the chat. Seeing it in the browser decided it, not the plan on paper.

**New ideas**
- Breakpoints, mobile first: plain classes are for phones; `md:` (768 px), `lg:` (1024 px) and `xl:` (1280 px) switch on at that width and override the smaller ones.
- Change the layout, don't squeeze: the chat has a floor (360 px). When there's no room, a column leaves instead.
- One state, many sizes: the same `narrowView` drives the phone screens and the 768-1279 px swap. CSS decides what each size shows; React only remembers which part is active.
- Hidden means no height: a hidden chat has `clientHeight` 0, so it never sends "read" for messages nobody can see (D20).
- Flex rows that never overlap: the part that may shrink gets `min-w-0` and `truncate` ("..."); parts that must stay whole get `shrink-0`.
- Word wrapping: `overflow-wrap: break-word` wraps between words, and breaks inside a word only when one word alone is too wide.
- Check the real build: at localhost:8080, rebuild web and hard-reload (Ctrl+Shift+R), or you're looking at old code.

**In my words** (draft by Claude Code, Adithya keeps or edits)
- What this task does: Parley now fits every screen, from a 360 px phone to a wide desktop. From 1280 px all four columns show. Below that, the files panel swaps places with the chat when you tap the name, and a phone shows one screen at a time. Buttons that don't work yet are hidden, so nothing on the live app looks broken.
- What I'd check first if it broke: rebuild web and hard-reload first, since an old build fooled me once. Then open DevTools' device toolbar at the width where it breaks and find the column that's too wide: usually a missing `min-w-0`, `shrink-0` or size prefix.
- What still confuses me: when two classes clash at the same size, like `hidden` and `flex` in one `cn(...)`, I think tailwind-merge keeps the last one. I'm not sure how it decides that across different sizes.

---

### Task 28: Parley live on AWS (one EC2 server, Terraform, HTTPS)
**What was built**
- Live at https://parley-adithya.duckdns.org (Mumbai, `ap-south-1`), on one t3.small server built by Terraform. Everything else is generic and runs on any Linux server (D29).
- Before any code:
  - `docker stats` on the laptop: the whole stack used about 490 MiB idle (RabbitMQ 159, two backends 169, worker 77, db 49, redis 27, web 9). With Ubuntu and Docker that's about 1 GB, so 2 GB plus 2 GB swap is enough, even for building on the server.
  - The account had no default VPC in Mumbai at all, so Terraform builds its own network.
  - Secret scan before going public: gitleaks over a mirror of the GitHub repo (every branch and all 27 PR refs, which GitHub shows to anyone once public), plus a check that no real `.env` value appears in any version of any file. Clean, so the repo went public.
- `deploy/aws/terraform/` (all AWS-only, D29):
  - `versions.tf`: Terraform `~> 1.16.0`, AWS provider `= 6.67.0` (it ships a minor every week, so a 4-week-old one, D27), and `default_tags` putting `project=parley` on everything.
  - `variables.tf`: region, server size, disk size.
  - `network.tf`: VPC `10.0.0.0/16`, one public subnet `10.0.1.0/24` in ap-south-1a, an internet gateway and a route table sending `0.0.0.0/0` through it. All free.
  - `server.tf`: a security group with only tcp 80 and 443 in; an IAM role that EC2 can wear, with only `AmazonSSMManagedInstanceCore`; Ubuntu 24.04 found through Canonical's SSM pointer; `cpu_credits = "standard"`; IMDSv2 only with hop limit 1 (added after the planner's review); an encrypted 20 GB gp3 disk; `ignore_changes = [ami]`; an Elastic IP.
  - `user_data.sh`: installs Docker and the Compose plugin from Docker's repo on first boot. Each `apt-get` waits up to 5 minutes for Ubuntu's own first-boot updates (`DPkg::Lock::Timeout=300`, also from the review).
  - `outputs.tf`: the IP, the instance id and the Session Manager command.
  - `.terraform.lock.hcl` is committed (it pins the provider). `.gitignore` keeps `.terraform/`, the state and saved plans (`*.tfplan`) out of Git.
- The plan was shown in plain words, reviewed by the planner (twice), saved to a file, and only that file was applied: 11 resources, about $22 a month in credits. Session Manager saw the server 15 s after it started.
- `docker-compose.prod.yml`, laid on top of `docker-compose.yml`: no ports for db, Redis and RabbitMQ (`!reset []`), web on 80 → 8080 and 443 → 8443 (`!override`), `restart: unless-stopped` on everything but `migrate`, logs capped at 3 × 10 MB, `COOKIE_SECURE=true`, Nginx reloading every 6 h, and a `certbot` service (`v5.8.0`) that checks for renewal every 12 h. The laptop file is unchanged, so the CI containers job still tests the local run.
- `deploy/server/nginx.prod.conf`: port 80 only serves `/.well-known/acme-challenge/` and redirects everything else with a 301. Port 443: the certificate at the fixed path `live/parley/`, TLS 1.2 and 1.3 only, and the same `/`, `sw.js` and `/api/` rules as T26. HSTS for one year (no preload, no includeSubDomains) was added only after https was proven.
- `deploy/server/` scripts:
  - `setup.sh [branch]`: Docker if it's missing, a 2 GB swap file, and `git clone` into `/opt/parley`. Safe to run again.
  - `.env.prod.example`: the 10 settings a server needs. Every secret was made on the server with `openssl rand -hex` and written straight into `.env` with `sed`, so it never showed on screen. The production VAPID keys were made with the backend image, on the server.
  - `first-cert.sh <domain> <email>`: a practice run on Let's Encrypt's test server, then the real certificate (certbot standalone on port 80), then `up -d --build`, then `certbot reconfigure` to webroot plus `renew --dry-run`. The deploy hook (`chgrp 101` + `chmod g+rX`) is saved with the certificate, so every renewal runs it.
  - `deploy.sh [web]`: pull, rebuild what changed, always recreate `web`, and clear old images. `web` leaves the backend copies running (D28).
- `deploy/README.md`: any Linux server, AWS with Terraform, and how to turn it all off.
- Checked on the live site:
  - From the internet: http → 301 → https with the path kept. A valid Let's Encrypt certificate (Oct 30, 2026 → Jan 28, 2027). TLS 1.1 refused. `/api/health` answered by A and B. Ports 80 and 443 open; 22, 5432, 6379, 5672, 15672, 8000, 8080 and 8443 never answer. The security group in AWS has exactly the two rules.
  - On the server: every service up and healthy, `migrate` exited 0, the key `-rw-r----- root 101`, renewal set to webroot with the hook saved, about 1 GB of 1.9 GB used, swap barely touched, disk 41% full.
  - Real IP: the backends logged the laptop's public IP, not Docker's gateway.
  - Ana on the laptop and Adi on an iPhone (Chrome): chat live, ticks, typing. The refresh cookie: `HttpOnly`, `Secure`, `SameSite=Lax`, rotated on every refresh.
  - Push: Adi's Chrome device saved (`fcm.googleapis.com`), and the worker logged `#10 ... sent` 5 s after the message. The notification had no message text, and clicking it opened the chat.
  - Failover: Adi's line on A, the other person's on B. `stop backend_a` mid-chat: new lines opened on B the same second, messages #11 to #19 went both ways while A was down, and the chat ended with 19 messages numbered 1 to 19 with no gaps, both bookmarks at 19.
  - `deploy.sh web`: pulled, recreated only `web`, HSTS showed on every https answer, and the backends kept running.
  - `terraform plan -destroy` shown, not run: the same 11 resources, nothing else.
- Found along the way:
  - AWS refuses an apostrophe in a security group rule's description ("Let's" became "Lets").
  - Git's `autocrlf` on Windows could turn `user_data.sh` into CRLF on a later checkout, and bash on the server would choke on the `\r`. Terraform strips it with `replace()`.
  - Non-root Nginx proven to fail on the key ("Permission denied" on `privkey.pem`, which certbot makes `-rw------- root`). The deploy hook's `chgrp`/`chmod` fixed it in the same local test.
  - A Session Manager shell may not set `$USER`, so `setup.sh` uses `id -un`.
  - A single file mounted into a container keeps the old version after `git pull` replaces it, so `deploy.sh` always recreates `web`.
  - The first "no notification": the browser's site permission was on, but nobody had clicked Parley's own "Turn on notifications" (in the gear menu), so no device was saved and the worker logged "skip: no devices". Once clicked, it worked.
  - iPhone keyboard: the message box could hide behind the keyboard and the header slid off screen (`h-svh` doesn't shrink for the keyboard). It's its own fix after this task (`fix/phone-keyboard`).
  - A new public IP gets scanned within minutes: a few `400 GET /` in Nginx's log, not from us.

**New ideas**
- Infrastructure as code (Terraform): servers described in files. `plan` compares the files with the state and with AWS and lists what would change. `apply` does it. `destroy` removes everything in the state. A saved plan (`-out`) means `apply` does exactly what was reviewed.
- State: Terraform's receipt of what it built (ids, IPs). It lives only on the laptop, never in Git. Without it, Terraform forgets what it made.
- A VPC is a private network. A subnet is a slice of it in one zone. The internet gateway is its door. The route table says "anything outside goes through the door", which is what makes the subnet public.
- Security group: a firewall in front of the server. Only listed ports come in. A dropped port gives no answer at all, unlike "refused", which means it's open but nothing listens.
- Session Manager: a shell through AWS. The server's agent calls out to AWS, and AWS never calls in. So there's no port 22 and no key file. The IAM role (instance profile) is what allows it.
- The metadata service (IMDS): where a server asks AWS about itself and gets its role's keys. IMDSv2 needs a token first, and hop limit 1 keeps containers from getting one.
- Elastic IP: a fixed public IP, so DNS is set once. Every public IPv4 costs money now, even attached.
- Let's Encrypt's HTTP check: it gives a secret, certbot puts it at `/.well-known/acme-challenge/...` on port 80, and Let's Encrypt fetches it from the internet. Only whoever controls the domain's server can do that. Certificates last 90 days and renew at 30 days left. Standalone (certbot answers port 80 itself) is used once; webroot (certbot drops the file, Nginx serves it) is used for renewals.
- Why port 80 only redirects: the check needs it, but the app is never served over plain http, where anyone on the network could read or change it.
- HSTS: the https answer tells the browser to skip http for this site for a year.
- Compose override files: a second file laid on top of the first. `!reset` empties a list and `!override` replaces it, so the laptop file stays as it is.
- Restart policies (`unless-stopped`), log rotation (`max-size`/`max-file`) and swap: what a server needs that a laptop doesn't.
- Turning it off: `destroy`, not stop. A stopped server's disk and IP still cost about $5.50 a month.

**In my words** (Adithya writes this)
- What Terraform plan, apply and destroy do: Terraform is a tool that builds servers from code. "Plan" is a dry run that lists exactly what it is about to create or change. "Apply" is the command that actually builds the servers, networks, and firewalls. "Destroy" is the undo button; it deletes everything Terraform created so you stop getting billed.

- Why there's no SSH port, and how you still get a shell: Hackers constantly scan the internet for open SSH ports (port 22) to guess passwords. Instead, Parley uses AWS Session Manager. The server reaches out to AWS to ask for commands, rather than AWS reaching in. Because there is no open port, hackers can't even try to break in, but I can still get a secure shell through the AWS console.

- How Let's Encrypt proves you own the domain, and why http only redirects: Let's Encrypt gives you a secret code and tells you to put it at a specific URL on your server. It then visits that URL from the outside. Since only the domain owner controls the server, passing the test proves ownership. Port 80 (HTTP) only redirects to Port 443 (HTTPS) because HTTP is unencrypted. If the app were served over HTTP, anyone on the same Wi-Fi could read your messages and passwords.

- Why db, Redis and RabbitMQ must have no open ports on a server: If their ports are open, the entire internet can try to connect to them, guess passwords, or flood them. They are internal helpers that only your backend servers need to talk to. By keeping their ports closed to the outside world, they become completely invisible and safe from the public internet.

---

### Fix: phone keyboard layout (after T28)
**What was built**
- `frontend/index.html`: the viewport meta gets `interactive-widget=resizes-content`. On Android Chrome the keyboard then shrinks the page instead of covering it. iPhones ignore it.
- `frontend/src/features/chat/useVisibleArea.ts` (new): a small hook used by the chat screen.
  - It listens to `visualViewport` (the part of the page you can actually see) and writes its height and top into two CSS variables, `--visible-height` and `--visible-top`.
  - It follows Safari's slide (`offsetTop`) only while a text box has the focus, which is when the keyboard is up. Otherwise the top stays at 0, so a bounce can't move the screen.
  - It ignores changes while you're pinch-zoomed in.
  - It adds the `page-locked` class to `<html>` while the chat screen shows, and removes it on log-out.
- `frontend/src/index.css`: `html.page-locked` turns off scrolling and bouncing on html and body (`overflow: hidden`, `overscroll-behavior: none`) and pins body (`position: fixed; inset: 0`). On an iPhone `overflow: hidden` alone didn't stop the bounce.
- `frontend/src/features/chat/ChatScreen.tsx`: `h-svh` is replaced by `fixed inset-x-0`, with the top and height taken from the two variables (falling back to `0px` and `100dvh`).
- `frontend/src/features/chat/Conversation.tsx`:
  - New scroll rules: my own send always jumps to the newest message. Their message only keeps me at the bottom if I was already there. If I've scrolled up, it doesn't pull me down.
  - A `ResizeObserver` keeps the list at the bottom when it gets shorter or taller (keyboard, "is typing..."), but only if I was at the bottom. It replaces the old `typing` effect.
  - `overscroll-contain` on the message list. The box's bottom space is `max(1rem, env(safe-area-inset-bottom))`, which is 1rem in a browser tab.
- `frontend/src/features/chat/MessageBox.tsx` and the Search box in `ChatColumn.tsx`: 16 px on phones (`text-base md:text-body`), so tapping them doesn't zoom. 15 px from 768 px up, as before.
- `frontend/src/features/chat/ChatColumn.tsx`: the gear menu closes on a tap or click outside it, and on Esc. The chat list gets `overscroll-contain`.
- `frontend/src/features/chat/SidePanel.tsx`: `overscroll-contain`.
- `frontend/src/features/auth/AuthCard.tsx`, `AuthProvider.tsx`: `min-h-svh` becomes `min-h-dvh`. These pages aren't locked, so they can still scroll with the keyboard.
- Checked:
  - iPhone over Wi-Fi (Vite `--host` at the laptop's IP): with the keyboard open, the header stays at the top, the box sits just above the keyboard, there's no zoom, and only the messages scroll. Closing the keyboard after scrolling up keeps your place.
  - iPhone: dragging on the header, the message box, an empty chat and a short chat list moves nothing (no grey strip).
  - Live site, with the branch put up for the test (`deploy.sh web`), in iPhone Chrome and Safari: a send jumps to the newest message, a scrolled-up iPhone doesn't jump when the laptop sends, and closing the keyboard leaves no shift. Edge notifications work after turning them on in the gear menu.
  - Gear menu: closes on a tap or click outside, and on Esc (laptop and iPhone).
  - Desktop spot-check (Edge DevTools): 1440 has four columns and the panel folds; 1024 has three columns and the name swaps in the panel with a back arrow; 390 is one screen at a time. Same as T27.
  - Lint and build clean.
- Found along the way:
  - Sending fails on `http://192.168.x.x`: `crypto.randomUUID()` only works on a secure page (https or localhost). So sending was tested on the live site instead.
  - The "inverted swipe" only happened where nothing could scroll (an empty chat, a short list, the header). The swipe moved the page itself, the page bounced, and the first hook followed iOS's slide the wrong way. A stale mid-bounce value also left the header cut off right after opening a chat.
  - `env(safe-area-inset-bottom)` is always 0 unless the page uses `viewport-fit=cover`. In a browser tab, Safari and Chrome already keep the page above the home bar, so we didn't add `cover` (it would push the layout under the notch in landscape).
  - Pull-to-refresh never worked and live chat doesn't need it, so no change.

**Why**
- Parley's link goes on the resume next, and recruiters will open it on a phone. On an iPhone, the keyboard hid the message box or pushed the header off screen, and the page stayed slid up after the keyboard closed.

**New ideas**
- Two viewports: the layout viewport is the page's full size. The visual viewport is the part you can see right now. On an iPhone the keyboard only shrinks the visual one and slides it, so `h-svh` (and even `h-dvh`) don't get shorter.
- `svh` / `dvh`: `svh` is the height with the browser's bars showing. `dvh` follows the bars as they show and hide. Neither knows about the iPhone keyboard.
- Lock the page, scroll a box: when the page itself can't move, a finger can only scroll a list inside it. `overscroll-behavior` stops a list's bounce from passing on to the page.
- iOS zooms into any text box under 16 px when you tap it. 16 px on phones fixes it without blocking pinch-zoom.
- "Stay at the bottom" is a memory, not a position: the list remembers whether I was at the bottom (`atBottom`) and only then follows new messages or a size change.
- Secure context: some browser features (`crypto.randomUUID`, service workers, push) only work on https or localhost. A phone on the laptop's Wi-Fi IP gets plain http.
- Clicking outside a menu: listen for `pointerdown` on the whole page while the menu is open, and close it unless the tap landed inside the menu's box (`ref.contains`).

**In my words** (draft by Claude Code, Adithya keeps or edits)
- What this fix does: It makes the chat work on an iPhone like a native app. When the keyboard opens, the header stays at the top, the message box sits right above the keyboard, and only the messages scroll. The page itself is locked so it doesn't bounce around when you drag your finger. It also stops Safari from zooming in when you tap the text box, and it makes sure new messages don't yank you to the bottom if you're busy reading older ones.
- What I'd check first if it broke: I would check if the page is locked (look for the `page-locked` class on the HTML element) and check what the `--visible-height` CSS variable is set to. Most importantly, I'd test on a real iPhone, because Chrome DevTools doesn't simulate the iOS keyboard correctly. Also, I'd remember that sending messages only works over HTTPS, so testing on a local Wi-Fi IP address won't work.
- What still confuses me: Why iOS decides to slide the page up instead of just shrinking it when the keyboard opens, and why `overflow: hidden` wasn't enough to stop the bounce until we forced the body to `position: fixed`.

---

### Task 29: Auto-deploy from GitHub, secrets in AWS, and an alarm
**What was built**
- Step 0, a fresh database on the live server: `down`, the `parley_db_data` volume removed (3 old test accounts), Redis emptied with `FLUSHALL`, then `up` (`migrate` built the tables again). Clean demo accounts Ana (laptop) and Ben (iPhone). The link is ready for the resume.
- `/api/health` shows `"version"`, the commit the image was built from (`ARG APP_VERSION` in the backend Dockerfile, placed last so the package layer stays cached). On the laptop it says `dev`.
- `deploy/aws/terraform/` (AWS-only, D29). Every change was a plan in plain words, an OK, then `apply`:
  - `ecr.tf`: two image stores, `parley-backend` and `parley-web`. Tags can't be overwritten, each image is scanned on push, only the last 10 are kept, and `force_delete` lets `destroy` remove them even with images inside.
  - `deploy.tf`:
    - Reads the GitHub OIDC provider that already existed for the delivery-delay project (a `data` source, so `destroy` never deletes it).
    - The role `parley-github-deploy`, which only this repo's `main` can use. It may push to (and read) the two stores, and run one SSM document on one server.
    - That document, `parley-deploy`, takes one input, a commit id (`^[0-9a-f]{7,40}$`). It runs `git fetch`, `git checkout --detach <commit>` and the deploy script as the repo's owner (ssm-user), not as root.
  - `server.tf`: the server's role may also pull images, read `/parley/prod/*` and write logs. A temporary "write `/parley/prod/*`" rule (`allow_secret_upload`) existed only while the secrets were stored, and the second apply removed it.
  - `monitoring.tf`: the log group `/parley/containers` (7 days), an SNS topic with the email, and two alarms. One fires on failed status checks for 2 minutes (or no data at all), the other on CPU above 80% for 15 minutes. Both also email when things are OK again.
  - `variables.tf`, `outputs.tf`: the repo in GitHub's id form, the alarm email (from a gitignored `terraform.tfvars`), the role ARN and the registry address.
  - In all: 14 added, 1 removed (the temporary write), 2 fixes. About $0.36 a month in credits.
- `deploy/aws/store-secrets.sh`, run once on the server: the 10 settings from `.env` became encrypted parameters under `/parley/prod/`. Values go in through stdin, so they never show on screen or in the process list. Then it reads everything back and compares, printing only "matches". The AWS CLI came from `sudo snap install aws-cli --classic`.
- `deploy/aws/deploy-from-ecr.sh` and `docker-compose.ecr.yml`:
  - `.env` comes from Parameter Store. It's written next to the old one and moved over it in one step, and the script stops if `JWT_SECRET` is missing.
  - Then: ECR login and pull; the helpers are recreated only if their settings changed; `migrate`.
  - `backend_a`, wait 15 s (Nginx finds its new address), `backend_b`, the worker.
  - `web` only if `frontend/`, `nginx.prod.conf` or a Compose file changed since the running version. It stops with SIGTERM (Nginx's fast stop).
  - Parley's own containers log to CloudWatch. The helpers keep local logs.
- `.github/workflows/deploy.yml`:
  - It starts after CI passes on `main` (`workflow_run`), or by hand with a version (the rollback), and never two at a time.
  - It checks out the exact commit CI tested, logs in with OIDC (`configure-aws-credentials@v6.3.0`), and builds and pushes only versions not already in ECR.
  - It runs `parley-deploy`, then checks that every answer from the live site shows the new version.
  - GitHub holds 4 variables and no secrets.
- `deploy/server/deploy.sh` refuses to run outside `${PARLEY_DIR:-/opt/parley}` and on a detached commit ("This server is deployed by GitHub Actions"). `deploy/README.md` got a part 3 for all of this.
- Follow-up (`fix/deploy-check`):
  - The live check asks only for the new version (not answers from both copies), and the rollback box ignores spaces.
  - Runners pinned to `ubuntu-24.04`.
  - `python:3.13.18-slim-trixie`, and `apk upgrade` in the web image (curl 8.22.0 → 8.23.0, brotli 1.2.0 → 1.2.1).
  - The health checks of RabbitMQ and the backends run every 30 s once a container is up, and every 1-2 s only while it starts.
- Checked:
  - First deploy from ECR (`95196b3`, by hand), with `/api/health` asked twice a second from the laptop. While `backend_a` was replaced, B answered all 22 asks. While `backend_b` was replaced, A answered all 18. Web was gone for ~9 s (its old, slow stop).
  - Merging PR #31 deployed `cdd1bb5` by itself: green, 871 asks over 15 minutes, 0 failures. Web was left running, since nothing it's built from changed.
  - Rollback by hand to `95196b3`: green, and `/api/health` showed it. Forward again to `cdd1bb5`: Ana and Ben sent 4 messages during it, all arrived once and in order, and "Reconnecting..." flashed.
  - Parameter Store matched `.env` exactly, and no secret ever showed on screen.
  - CloudWatch has one log stream per Parley container. The test alarm (`set-alarm-state`) sent the ALARM email, and the OK email came 1.5 minutes later by itself.
  - "Only main can deploy": the Deploy workflow run by hand on `fix/deploy-check` was refused at the AWS login ("Not authorized"), and the server got no command.
- Found along the way:
  - Redis saves to disk when it stops, so restarting it doesn't empty it. `FLUSHALL` does.
  - Pasting several lines into Session Manager mixes them up. One line at a time works.
  - Stopping web took 10.3 s: Nginx's default stop waits for every open live line. Hence SIGTERM.
  - The first automatic deploy failed twice:
    - GitHub's ID card for this repo uses the newer immutable form, `repo:AdithyaChauhan@91404342/parley@1423740237:ref:refs/heads/main`, so the exact match failed.
    - Then the push was refused at its last step. CloudTrail showed every layer uploaded and then `ecr:BatchGetImage` denied: Docker asks whether the image exists before saving it.
    - Also, the web image was built from `./web` instead of `frontend/`.
  - "Both copies must answer" can't pass while someone chats: Nginx's least_conn sends quick asks to the copy with fewer open live lines.
  - A version pasted with a trailing space was refused by the format check.
  - iPhone browser tabs can't get web push at all. iOS allows it only for apps added to the Home Screen.
  - The idle server used ~19% CPU. Measured per container over 60 s: RabbitMQ 9%, each backend 3.7%. It was their health checks, which start a whole program (Erlang or Python) every 5 seconds.
  - ECR's scan found 8 critical and 17 high in the web image (curl and brotli from Alpine), and 4 high in the backend (glibc and zlib from Debian, with no fix published yet).

**New ideas**
- CI/CD: CI tests every change. CD (continuous deployment) puts a change that passed live by itself.
- OIDC: for each run, GitHub signs an ID card saying which repo and branch it is. AWS checks the card against the role's trust rule (exact match) and hands out a pass that lasts an hour. There's no stored key that could leak.
- Least privilege: each role gets only what its job needs. GitHub can push images and press one button. The server can pull, read its secrets and write logs.
- An image registry (ECR) stores versions under tags. Immutable tags mean a version name always means the same image. A lifecycle rule deletes old ones, and a scan lists known security holes in the packages inside.
- SSM Run Command: AWS passes a command to the server's agent, so there's no SSH. A custom document limits it to one script with one checked input.
- Parameter Store SecureString: a setting encrypted with an AWS key. Whoever's role allows reading it can read it, and nobody else.
- Rolling restart: replace one copy at a time and wait until it's healthy, so the other copy carries everyone. Wait for the load balancer to notice before touching the second one.
- Expand, then contract: add new columns in one deploy, remove old ones in a later one, because the old copy briefly runs on the new tables.
- Rollback = deploy an older version again. It works because images can't change and the server checks out that commit's files too.
- CloudWatch: logs (Docker's `awslogs` driver), metrics, and alarms that send to SNS (email). "Missing data counts as failing" also catches a server that's gone silent.
- CloudTrail: AWS's own record of every call, including refused ones. That's how the missing permission was found.
- Health checks cost CPU, since each one starts a program. `start_period` + `start_interval` check often only while a container starts.
- Nginx stops two ways. SIGQUIT is graceful (waits for open connections). SIGTERM is fast (closes them, and the apps reconnect).

**In my words** (Adithya writes this)
- How GitHub gets into AWS without a stored key (OIDC): Instead of saving a permanent AWS password in GitHub (which could be stolen), GitHub and AWS use OIDC. For every deployment, GitHub creates a temporary, cryptographically signed "ID card" and hands it to AWS. AWS checks the card, sees it's from my specific repo on the main branch, and hands back temporary keys that expire in 1 hour. Nothing permanent is ever saved.

- Why the copies restart one at a time: If we restarted both backend servers at the exact same time, the live chat would go down while they rebooted. By doing a rolling restart, Copy A restarts while Copy B handles all the traffic. Once A is healthy again, B restarts. The user never notices a drop in service.

- Where the secrets live now and who can read them: Secrets (like database passwords and JWT keys) no longer live in a plain text file on the server. They live in the AWS Parameter Store as encrypted SecureStrings. Only the server's specific AWS IAM role is allowed to read them. If a hacker breaks in, they need the server's temporary AWS credentials to decrypt the values.

- What happens when the alarm fires: AWS CloudWatch watches the server. If the CPU stays above 80% for 15 minutes, or if the server stops reporting its status, the alarm triggers an SNS topic. That topic immediately sends an email to my inbox telling me the server is struggling. When the server recovers, it sends a second email saying the state is OK again.
