// Server times are UTC. new Date() reads them, and these helpers show them
// in your own time zone.

// "11:15"
export function clockTime(iso: string) {
  return new Date(iso).toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" })
}

// For the chat list: "11:15" today, "Yesterday", then "15.09" (or "15.09.2025" for an older year)
export function listTime(iso: string) {
  const date = new Date(iso)
  const today = new Date()
  const yesterday = new Date()
  yesterday.setDate(today.getDate() - 1)

  if (date.toDateString() === today.toDateString()) return clockTime(iso)
  if (date.toDateString() === yesterday.toDateString()) return "Yesterday"

  const day = String(date.getDate()).padStart(2, "0")
  const month = String(date.getMonth() + 1).padStart(2, "0")
  return date.getFullYear() === today.getFullYear() ? `${day}.${month}` : `${day}.${month}.${date.getFullYear()}`
}
