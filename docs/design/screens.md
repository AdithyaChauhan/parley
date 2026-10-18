# Parley: Screen Sketches

Layout for every screen. Colors, font, sizes and shapes are in `look.md`.
The main screen matches reference screenshot 1 (see D8). Names in the sketches are made up.

## 1. Main screen (desktop)

```
+--------+------------------+-----------------------------+------------------+
| logo   |   [avatar]    (*)| Group Chat [Messages] [Part]|  [group photo] > |
|        |   Your name      |-----------------------------|   Group name     |
| icons  |  [available v]   | (o) Name, 11:24 AM          |   10 members     |
|  ...   | [Search.......]  |     [their bubble.......]   | [Files] [Links]  |
| [act]| | Last chats   + : |          You, 11:26 AM      | File type      : |
|  ...   | (o) Name   11:15 |      [my bubble.........]   | [D] Documents  > |
|        |     typing...    |                             | [P] Photos     > |
|        | (o) Name   11:15 | (..) Mira is typing         | [M] Movies     > |
| [me]   | (o) Name   11:15 | [Write a message.. :) @] [>]| [O] Other      > |
+--------+------------------+-----------------------------+------------------+
```
`(*)` is the settings gear. The `>` beside the group photo folds the side panel.

1. **Icon rail** (about 90px): logo at the top, 6 icons, your avatar at the bottom. The active icon sits on a light teal tile, with a teal bar on its right edge.
2. **Chat column** (about 320px):
   - No title on desktop: your profile is the top of the column. A settings gear sits in its top-right corner.
   - Your profile: compact avatar (about 64px) with a green online dot, your name, status pill.
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
- No title on desktop. A small fold button (`>`) sits in the panel's top-right corner.
- Group photo, group name, member count.
- Two stat tiles: all files, all links.
- The file type list: documents, photos, movies and so on, each on its own colored tile.

**Folded** (screenshot 3): the panel shrinks to a thin strip of icons, with a small open button (`<`) at the top.

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

1. The chat column first, with a "Chat" title above the profile.
2. Tapping a chat opens the conversation full screen, with a back arrow.
3. Tapping the conversation's title opens the side panel full screen, with a back arrow and a "Shared files" title. It never folds on a phone.
4. The icon rail becomes a bar at the bottom.

## Not copied (D8)

The logo, the people's names and the photos. Parley uses its own logo, made-up names, and initials or generated avatars. The README credits the reference design.
