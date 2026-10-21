// The shapes the backend sends (T14), and the ones the screen adds itself.
// Times arrive as UTC text with a time zone, like "2026-10-22T09:15:00+00:00".

// Avatar colors: soft tints from docs/design/look.md
export type Tint = "teal" | "purple" | "yellow" | "red"

// sending = small clock, sent = one grey tick, delivered = two grey, read = two teal
export type Tick = "sending" | "sent" | "delivered" | "read"

// One row of the chat list (GET /api/chats, and the reply to POST /api/chats/direct)
export type ChatSummary = {
  id: string
  kind: string // "direct" for now. Groups come in v2.
  name: string // the other person's name in a direct chat
  last_message: { seq: number; preview: string; created_at: string } | null
  unread: number
}

// One message as the server sends it
export type ServerMessage = {
  id: string
  chat_id: string
  seq: number
  sender_id: string
  client_msg_id: string
  body: string
  created_at: string
}

// GET /api/chats/{id}/messages: up to 30, newest first
export type MessagePage = {
  messages: ServerMessage[]
  has_more: boolean // older messages are waiting above these
}

// A message on screen. Until the server answers, it has no number (seq) yet.
// clientMsgId stays the same before and after, so it's the key that matches them.
export type Message = {
  clientMsgId: string
  seq: number | null
  senderId: string
  body: string
  createdAt: string
  status: "sending" | "failed" | "sent"
}

export function fromServer(message: ServerMessage): Message {
  return {
    clientMsgId: message.client_msg_id,
    seq: message.seq,
    senderId: message.sender_id,
    body: message.body,
    createdAt: message.created_at,
    status: "sent",
  }
}

// Picks a tint from an id, so the same chat always gets the same color
const tints: Tint[] = ["teal", "purple", "yellow", "red"]

export function tintFor(id: string): Tint {
  let sum = 0
  for (const char of id) sum += char.charCodeAt(0)
  return tints[sum % tints.length]
}
