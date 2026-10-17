# Parley: Project Plan

Parley is a real-time chat web app, like WhatsApp Web. It's a portfolio project to learn and show backend system design.

**How to use this file**
- One task at a time. Each task = one branch = one pull request.
- "You are here" shows the current task and its brief.
- After a pull request merges, Adithya tells the planning chat. The planner sends back a new PLAN.md (box ticked, "You are here" moved to the next task). Adithya replaces the file, and that goes in the next task's branch.
- Only the planner (chat Claude) writes task briefs. Claude Code never edits this file. It can only suggest changes.
- Adithya may write a file himself if he wants. He tells Claude Code, so it knows.
- Each task's "Done when" also needs the task's "In my words" in LEARNING.md filled in by Adithya.

---

## You are here

### Task 2: The look
- **Branch:** `docs/the-look`
- **Goal:** choose Parley's colors, font and logo idea, and sketch every screen: main screen, side panel (open and folded), upload view, sign-up, log-in and phone. Phase 1 builds these screens, so they need a plan first.
- **Files:** `docs/reference/` (the 3 reference screenshots), `docs/design/look.md`, `docs/design/screens.md`
- **Steps:**
  1. Make the branch `docs/the-look`.
  2. Copy the 3 reference screenshots into `docs/reference/`, named `reference-1.webp`, `reference-2.webp` and `reference-3.webp`. Parley matches their layout, colors, spacing, shapes and font style (see D8). Do not copy any name, logo or photo from them.
  3. Create `docs/design/look.md` from "The look" below.
  4. Create `docs/design/screens.md` from the "Screen sketches" below.
  5. Adithya changes anything he doesn't like, then commit, open a pull request and merge.
- **Done when:** both design files and the reference screenshots are on `main`, and Adithya has said the look matches the screenshots.

**The look: match the reference screenshots closely.** Colors were measured from the screenshots.

Colors:
- Page behind the app, `#DCE0E8` (soft blue-grey).
- App card, `#FFFFFF`, with big rounded corners (28px).
- Conversation area background, `#EDF0F6`, in its own rounded panel (16px).
- Their bubble, `#FFFFFF`. My bubble, `#D1D3E4` (soft lavender-grey).
- Teal accent, `#00A389`: send button, active icon, the bar beside the active icon, @mentions, "Real estate"-style highlighted words.
- Light teal tint, `#E2F4F3`: active icon's tile, the "+" button, the selected stat tile, the active tab (`#D1E8E7`).
- Status pill ("available"), `#BDE8DE` with teal text.
- Search box, `#EFF3F6`. Selected chat row, `#F5F7FB`.
- Main text, `#28283A`. Soft text (previews, times, captions), `#8A8CA0`. Icons in the rail, `#C3C3D3`.
- Online dot, `#09C2A3` (measured).
- Unread count: a small round pill, teal `#00A389`, white number. Not in the screenshots, so it uses the teal accent.
- Ticks (not in the screenshots): one or two grey `#B4B6C8` ticks for sent and delivered. Two teal `#00A389` ticks for read.
- Error, `#E5484D` (soft red, close to the red in the logo area). Error text sits under the field, 12px.
- File type tiles: purple `#E6E6FA`, yellow `#FBF0D9`, teal `#DDF3F4`, red `#FCE4E4`, each with a darker icon of the same color.

Font: a rounded, geometric font. The screenshots look like Sofia Pro, which is paid. Use **Outfit** from Google Fonts (free and very close). Names 18px, headers 22px, body 15px, small labels 12px.

Shapes:
- Bubbles: 16px rounded corners, but one corner stays sharp. Their bubble: top-left is sharp (next to the avatar). My bubble: bottom-right is sharp.
- Above each bubble, a small label: "Name, 11:24 AM" (12px, main text).
- Spacing: steps of 4px (4, 8, 12, 16, 24, 32). Most gaps in the screenshots are 16px or 24px.
- Buttons and tiles: 12px corners. Round avatars. Soft shadows, almost invisible.

**Screen sketches (match screenshot 1):**
```
+--------+------------------+-----------------------------+------------------+
| logo   | (<) Chat         | Group Chat [Messages] Partic| (>) Shared files |
|        |   [avatar]       |-----------------------------|   [group photo]  |
| icons  |   Your name      | (o) Name, 11:24 AM          |   Group name     |
|  ...   |  [available v]   |     [their bubble........]  |   10 members     |
| [act]| | [Search.......]  |          You, 11:26 AM      | [All files][Links|
|  ...   | Last chats  + :  |       [my bubble.........]  |  File type     : |
|        | (o) Name   11:15 |                             | [D] Documents  > |
|        |     typing...    | (..) Robert is typing       | [P] Photos     > |
| [me]   | (o) Name   11:15 | [Write your message... :) @] [>]| [M] Movies  > |
+--------+------------------+-----------------------------+------------------+
```
1. Icon rail (about 90px): logo at the top, 6 icons, your avatar at the bottom. The active icon sits on a light teal tile, with a teal bar on its right edge.
2. Chat column (about 320px): back button and "Chat" title. Your profile: big avatar with a green online dot, name, status pill. Search box. "Last chats" with a "+" and a menu. Rows: avatar (or initials on teal tint), name, time, one-line preview. "typing..." replaces the preview while someone types.
3. Conversation: title, then "Messages" and "Participants" tabs. Messages with avatar, name and time label, and bubble. "Robert is typing" at the bottom. A white message box with emoji and attach icons, and a teal send button.
4. Side panel (about 320px): "Shared files", group photo, name, member count, two stat tiles (all files, all links), and the file type list. It folds into a thin strip of icons (screenshot 3).
5. Drag-and-drop upload view (screenshot 2): a dashed border over the conversation, a big teal upload circle, "Upload your file". Screen only for now; real uploads come in v2.

Sign-up and log-in: one white card (28px corners) on the `#DCE0E8` page, same font and teal, logo at the top, soft grey inputs like the search box, a teal button.

Phone (D2): one column at a time. Chat column first. Tapping a chat opens the conversation full screen, with a back arrow. The side panel opens as a full screen too. The icon rail becomes a bottom bar. Details come in T4.

Not copied (D8): the logo, the people's names and the photos. Parley uses its own logo, made-up names and initials or generated avatars. The README credits the reference design.

Ask Adithya one question at the end of the task: "Do you like these colors and this font, or what would you change?"

---

## All tasks

### Phase 0: Setup
- [x] T1. Repo and plan files
- [ ] T2. The look: Parley's colors, fonts and logo, plus screen sketches using the reference layout (reference screenshots go in `docs/reference/`)

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