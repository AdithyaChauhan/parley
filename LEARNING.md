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
