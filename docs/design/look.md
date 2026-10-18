# Parley: The Look

Parley matches the reference screenshots closely: layout, colors, spacing, shapes and font style (see D8). The colors were measured from the screenshots.

Not copied: the logo, the people's names and the photos. Parley uses its own logo, made-up names, and initials or generated avatars. The README credits the reference design.

## Colors

| Name | Hex | Used for |
|---|---|---|
| Page | `#DCE0E8` | The page behind the sign-up and log-in card (soft blue-grey) |
| App background | `#FFFFFF` | The main screen, which fills the whole window, and the sign-up and log-in card |
| Conversation area | `#EDF0F6` | The conversation's own rounded panel |
| Their bubble | `#FFFFFF` | Messages from other people |
| My bubble | `#D1D3E4` | Messages I sent (soft lavender-grey) |
| Teal accent | `#00A389` | Send button, active icon, the bar beside the active icon, @mentions, highlighted words |
| Light teal tint | `#E2F4F3` | Active icon's tile, the "+" button, the selected stat tile |
| Active tab | `#D1E8E7` | The active tab |
| Status pill | `#BDE8DE` | The "available" pill, with teal text |
| Search box | `#EFF3F6` | The search box |
| Selected chat row | `#F5F7FB` | The chat row that is open |
| Main text | `#28283A` | Names, message text |
| Soft text | `#8A8CA0` | Previews, times, captions |
| Rail icons | `#C3C3D3` | Icons in the icon rail |
| Online dot | `#09C2A3` | The green dot on an avatar (measured) |
| Unread count | `#00A389` | A small round pill with a white number (uses the teal accent) |
| Error | `#E5484D` | Soft red for errors. Error text sits under the field, 12px |
| Border | `#E0E0E0` | Dividers and input outlines (measured from screenshot 1) |

### Ticks

Not in the screenshots, so Parley picks its own.

| Tick | Color |
|---|---|
| Sent | One grey tick, `#B4B6C8` |
| Delivered | Two grey ticks, `#B4B6C8` |
| Read | Two teal ticks, `#00A389` |

### File type tiles

Each tile has a darker icon of the same color. Avatars use the same pairs: initials in the icon color on the tile color.

| Name | Tile | Icon |
|---|---|---|
| Purple | `#E6E6FA` | `#5B5FE0` |
| Yellow | `#FBF0D9` | `#C49A45` |
| Teal | `#DDF3F4` | `#2E9FAA` |
| Red | `#FCE4E4` | `#D0605A` |

## Font

A rounded, geometric font. The screenshots look like Sofia Pro, which is paid. Parley uses **Outfit** from Google Fonts, which is free and very close.

| Text | Size |
|---|---|
| Headers | 22px |
| Names | 18px |
| Body | 15px |
| Small labels | 12px |

## Shapes

- Main screen: fills the whole browser window, with no outer frame or outer rounded corners (D8).
- Sign-up and log-in card: 28px rounded corners. Only these screens use the card.
- Conversation panel: 16px rounded corners.
- Bubbles: 16px rounded corners, with one corner kept sharp.
  - Their bubble: the bottom-left corner is sharp (next to the avatar, which sits at the bubble's bottom).
  - My bubble: the bottom-right corner is sharp.
- Above each bubble, a small label: "Name, 11:24 AM" (12px, main text).
- Spacing: steps of 4px (4, 8, 12, 16, 24, 32). Most gaps are 16px or 24px.
- Buttons and tiles: 12px corners.
- Avatars are round.
- Shadows are soft, almost invisible.
