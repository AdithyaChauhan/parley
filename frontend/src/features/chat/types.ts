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
  other_user_id: string | null // the other person in a direct chat, to match presence news
  online: boolean // the other person has Parley open right now (D22)
  last_seen: string | null // when their app was last seen; null = unknown
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

// One person's tick bookmarks in a chat (D9)
export type MemberBookmarks = {
  user_id: string
  delivered_up_to: number // every message up to this number reached their device
  read_up_to: number
}

// GET /api/chats/{id}/messages: up to 30, newest first
export type MessagePage = {
  messages: ServerMessage[]
  has_more: boolean // older messages are waiting above these
  members: MemberBookmarks[] // everyone's bookmarks, so ticks are right after a reload
}

// What the server pushes down the live line (D19, D20)
export type LiveEvent =
  | { type: "hello"; data: { user_id: string; copy: string } } // copy: which backend copy picked up (D28)
  | { type: "message.new"; data: ServerMessage }
  | { type: "receipt"; data: { chat_id: string; user_id: string; delivered_up_to: number; read_up_to: number } }
  | { type: "typing"; data: { chat_id: string; user_id: string } }
  | { type: "presence"; data: { user_id: string; online: boolean; last_seen: string | null } } // came online or went offline (D22)
  | { type: "pong"; data: Record<string, never> } // the answer to the app's heartbeat ping (D21)

// A message on screen. Until the server answers, it has no id or number (seq) yet.
// clientMsgId stays the same before and after, so it's the key that matches them.
// sending = in the outbox, going out in its turn. waiting = no answer (offline),
// goes out when the line is back (D21). failed = refused, tap to retry.
export type Message = {
  id: string | null
  clientMsgId: string
  seq: number | null
  senderId: string
  body: string
  createdAt: string
  status: "sending" | "waiting" | "failed" | "sent"
}

export function fromServer(message: ServerMessage): Message {
  return {
    id: message.id,
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
