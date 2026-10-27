# Parley: Screen Sketches

Layout for every screen. Colors, font, sizes and shapes are in `look.md`.
The main screen matches reference screenshot 1 (see D8). Names in the sketches are made up.

## 1. Main screen (desktop)

```
+--------+------------------+-----------------------------+------------------+
| logo   |   [avatar]    (*)| (o) Name                    |    [photo]     > |
|        |   Your name      |     last seen today at 11:15|    Name          |
| [Chats]| [Search.......]  |-----------------------------|  last seen ...   |
|        | Last chats     + | (o) Name, 11:24 AM          |                  |
|        | (o) Name   11:15 |     [their bubble.......]   | [ No files yet ] |
|        |     typing...    |          You, 11:26 AM      |                  |
|        | (o) Name   11:15 |      [my bubble.........]   |                  |
|        |                  | (..) Mira is typing         |                  |
| [me]   |                  | [Write a message...    ] [>]|                  |
+--------+------------------+-----------------------------+------------------+
```
`(*)` is the settings gear. The `>` beside the photo folds the side panel.

No dead buttons (D8): anything that doesn't work yet is hidden, not shown as "coming soon".

1. **Icon rail** (about 90px, from 768 px): logo at the top, the Chats icon right under it, your avatar at the bottom. Chats sits on a light teal tile, with a teal bar on its right edge. The Status (eye) and calls icons come back only with those features; Dashboard, Tasks and Stats are gone for good (D8).
2. **Chat column** (about 320px):
   - No title: your profile is the top of the column. A settings gear sits in its top-right corner (notifications, log out).
   - Your profile: compact avatar (about 64px) with a green online dot, and your name. "Reconnecting..." shows under the name only while the live line is down.
   - Search box.
   - "Last chats" with a "+" to start a chat.
   - Rows: avatar (or initials on teal tint), name, time, one-line preview.
   - Unread count: a teal pill under the time in a chat row.
   - "typing..." replaces the preview while someone types.
3. **Conversation:**
   - The other person's avatar, name, and "online" or "last seen". No tabs: in v2, a group's members show in the side panel.
   - Each message: avatar, a "Name, time" label, then the bubble.
   - Ticks: beside the time on my bubble.
   - "Mira is typing" at the bottom.
   - A white message box with a teal send button. Attach comes back with files, and emoji with reactions (both v2, D8).
4. **Side panel** (about 320px): see section 2.

## 2. Side panel (open and folded)

**Open** (screenshot 1, about 320px):
- No title. A small fold button (`>`) sits in the panel's top-right corner.
- Photo, name, and "online" or "last seen" in a 1:1 chat (a group's members come in v2).
- "No files yet" until real files arrive in v2. The reference's stat tiles and file type list come back then (D8).

**Folded** (screenshot 3): the panel shrinks to a thin strip with just the open button (`<`) and the avatar.

**By window width** (D8):
- 1280 px and up: its own column, open or folded as above. Starts open.
- 768-1279 px: no column. Tapping the name at the top of the conversation puts the panel in the conversation's place, with a back arrow (no title) to return. The chat list stays.

## 3. Upload view

Hidden until v2 (D8): attach and file drop come back with real files. Dropping a file on the conversation does nothing for now.
The v2 screen matches screenshot 2: a dashed border over the conversation, a big teal upload circle, and the words "Upload your file".

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

## 6. Window sizes

```
 1280 px and up   rail | list | chat | side panel (folds to a strip)
 1024-1279 px     rail | list | chat or side panel (tap the name to swap)
 768-1023 px      rail | narrower list | chat or side panel
 under 768 px     one screen at a time, no bottom bar
```

The conversation is never narrower than 360 px. Bubbles are at most 75% of its width and wrap between words.

**Phone** (under 768 px), one column at a time (D2, D8):

1. The chat column first. No header: the profile (with the gear) is the top.
2. Tapping a chat opens the conversation full screen, with a back arrow to the list.
3. Tapping the conversation's title opens the side panel full screen, with a back arrow to the conversation and no title. It never folds on a phone.
4. No bottom bar: with only Chats, it would be one button that does nothing (D8). The rail shows from 768 px.

## Not copied (D8)

The logo, the people's names and the photos. Parley uses its own logo, made-up names, and initials or generated avatars. The README credits the reference design.
