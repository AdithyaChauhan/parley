// Status (D41): texts and photos that last 24 hours, seen by the people I
// have a direct chat with. The shapes GET /api/status sends.

export type StatusItem = {
  id: string
  user_id: string
  kind: "text" | "image"
  body: string // a text status's words, or a photo's caption
  color: number // a text status's background, 0-5 (STATUS_COLORS)
  width: number | null // photos only
  height: number | null
  preview: string | null // a tiny copy of the photo, shown until the real one arrives
  posted_at: string
  expires_at: string
  viewed: boolean // have I seen it (always true for mine)
  views: number | null // mine only: how many people saw it
}

export type PersonStatuses = {
  user_id: string
  name: string
  statuses: StatusItem[] // oldest first, the order they're watched in
  all_viewed: boolean
}

export type StatusFeed = {
  mine: StatusItem[]
  people: PersonStatuses[] // newest status first
}

export type Viewer = { user_id: string; name: string; viewed_at: string }

// Text status backgrounds, by number. The server only knows the number.
export const STATUS_COLORS = ["#2a9d8f", "#6d5bd0", "#d9822b", "#c2415d", "#3d7fc4", "#4a5568"]

// What a reply to a status carries: a small copy of it, so the reply still
// makes sense after the status is gone (D41)
export type StatusQuote = {
  id: string
  kind: "text" | "image"
  body: string
  color: number
  preview: string | null
}
