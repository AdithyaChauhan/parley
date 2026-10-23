// Server times are UTC. new Date() reads them, and these helpers show them
// in your own time zone.

// "11:15"
export function clockTime(iso: string) {
  return new Date(iso).toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" })
}

// "today", "yesterday", then "15.09" (or "15.09.2025" for an older year)
function dayLabel(iso: string) {
  const date = new Date(iso)
  const today = new Date()
  const yesterday = new Date()
  yesterday.setDate(today.getDate() - 1)

  if (date.toDateString() === today.toDateString()) return "today"
  if (date.toDateString() === yesterday.toDateString()) return "yesterday"

  const day = String(date.getDate()).padStart(2, "0")
  const month = String(date.getMonth() + 1).padStart(2, "0")
  return date.getFullYear() === today.getFullYear() ? `${day}.${month}` : `${day}.${month}.${date.getFullYear()}`
}

// For the chat list: "11:15" today, "Yesterday", then "15.09"
export function listTime(iso: string) {
  const day = dayLabel(iso)
  if (day === "today") return clockTime(iso)
  if (day === "yesterday") return "Yesterday"
  return day
}

// For the conversation header: "last seen today at 11:15", "last seen 15.09 at 18:40",
// or "last seen recently" when the server doesn't know (D22)
export function lastSeenText(iso: string | null) {
  if (!iso) return "last seen recently"
  return `last seen ${dayLabel(iso)} at ${clockTime(iso)}`
}
