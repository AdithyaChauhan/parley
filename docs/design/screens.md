# Parley: Screen Sketches

Layout for every screen. Colors, font, sizes and shapes are in `look.md`.
The main screen matches reference screenshot 1 (see D8). Names in the sketches are made up.

## 1. Main screen (desktop)

```
+--------+------------------+-----------------------------+------------------+
| logo   | (<) Chat         | Group Chat [Messages] [Part]| (>) Shared files |
|        |   [avatar]       |-----------------------------|   [group photo]  |
| icons  |   Your name      | (o) Name, 11:24 AM          |   Group name     |
|  ...   |  [available v]   |     [their bubble.......]   |   10 members     |
| [act]| | [Search.......]  |          You, 11:26 AM      | [Files] [Links]  |
|  ...   | Last chats   + : |      [my bubble.........]   | File type      : |
|        | (o) Name   11:15 |                             | [D] Documents  > |
|        |     typing...    | (..) Mira is typing         | [P] Photos     > |
| [me]   | (o) Name   11:15 | [Write a message.. :) @] [>]| [M] Movies     > |
+--------+------------------+-----------------------------+------------------+
```

1. **Icon rail** (about 90px): logo at the top, 6 icons, your avatar at the bottom. The active icon sits on a light teal tile, with a teal bar on its right edge.
2. **Chat column** (about 320px):
   - Back button and "Chat" title.
   - Your profile: big avatar with a green online dot, your name, status pill.
   - Search box.
   - "Last chats" with a "+" and a menu.
   - Rows: avatar (or initials on teal tint), name, time, one-line preview.
   - Unread count: a teal pill under the time in a chat row.
   - "typing..." replaces the preview while someone types.
3. **Conversation:**
   - Title, then "Messages" and "Participants" tabs.
   - Each message: avatar, a "Name, time" label, then the bubble.
   - Ticks: beside the time on my bubble.
   - "Mira is typing" at the bottom.
   - A white message box with emoji and attach icons, and a teal send button.
4. **Side panel** (about 320px): see section 2.

## 2. Side panel (open and folded)

**Open** (screenshot 1, about 320px):
- "Shared files" title.
- Group photo, group name, member count.
- Two stat tiles: all files, all links.
- The file type list: documents, photos, movies and so on, each on its own colored tile.

**Folded** (screenshot 3): the panel shrinks to a thin strip of icons.

## 3. Upload view

Matches screenshot 2. Drag and drop a file over the conversation:
- A dashed border over the conversation.
- A big teal upload circle.
- The words "Upload your file".

Screen only for now. Real uploads come in v2 (see D8).

## 4. Sign-up screen

- One white card (28px corners) on the `#DCE0E8` page.
- Same font and teal as the main screen.
- Logo at the top.
- Fields: name, email, password. Soft grey inputs, like the search box.
- One teal button.
- A small link to switch to log-in.

## 5. Log-in screen

The same card as sign-up, with no name field.

- Logo at the top.
- Fields: email, password.
- One teal button.
- A small link to switch to sign-up.

## 6. Phone

One column at a time (D2):

1. The chat column first.
2. Tapping a chat opens the conversation full screen, with a back arrow.
3. The side panel opens as a full screen too.
4. The icon rail becomes a bar at the bottom.

The details come in T4.

## Not copied (D8)

The logo, the people's names and the photos. Parley uses its own logo, made-up names, and initials or generated avatars. The README credits the reference design.
