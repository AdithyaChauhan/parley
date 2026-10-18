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
- What this task does, as if explaining to an interviewer:
- What I'd check first if it broke:
- What still confuses me:

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