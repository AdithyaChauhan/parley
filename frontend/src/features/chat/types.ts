// The shapes the backend sends (T14), and the ones the screen adds itself.
// Times arrive as UTC text with a time zone, like "2026-10-22T09:15:00+00:00".

// Avatar colors: soft tints from docs/design/look.md
export type Tint = "teal" | "purple" | "yellow" | "red"

// sending = small clock, sent = one grey tick, delivered = two grey, read = two teal
export type Tick = "sending" | "sent" | "delivered" | "read"

// Which part takes the shared spot on a smaller screen (D8). On a phone: only
// that one shows. 768-1279px: the list always shows, and "panel" takes the
// conversation's place. From 1280px everything shows and this is ignored.
export type NarrowView = "list" | "chat" | "panel"

// Someone named in a group note: who did it, or who it was done to
export type Person = { id: string; name: string }

// What a group note says happened (D37). The server keeps the facts, and the
// app writes the words (groupNotes.ts).
export type SystemData = {
  event: "created" | "added" | "removed" | "left" | "renamed" | "made_admin"
  by: Person
  users?: Person[] // added, removed, made admin (and the first members, for created)
  name?: string // the group's name, for created and renamed
  new_admin?: Person // left: the last admin left, so this member became admin
}

// What a file message holds (D38). The server never opens the file; these
// facts come from the sender's app and the store.
export type FileCategory = "image" | "document" | "voice"
export type FileData = {
  file_id: string
  name: string
  type: string
  size: number
  category: FileCategory
  width?: number | null
  height?: number | null
  preview?: string | null // a tiny copy of a picture, shown until the real one arrives
  duration_ms?: number | null // voice notes
}

// An event's data: which message it changed (D39)
export type EventData = { target_seq: number }

// The six reactions (D39). They must match the server's list exactly.
export const REACTIONS = ["👍", "❤️", "😂", "😮", "😢", "🙏"]
// Emoji → the people who picked it
export type Reactions = Record<string, string[]>

// One row of the chat list (GET /api/chats, and the reply to creating a chat or group)
export type ChatSummary = {
  id: string
  kind: "direct" | "group"
  name: string // the other person's name in a direct chat, the group's name in a group
  last_message: {
    seq: number
    preview: string
    created_at: string
    kind: "text" | "system" | "file"
    sender_id: string
    sender_name: string | null
    data: SystemData | FileData | null
    deleted: boolean // deleted for everyone (D39)
  } | null
  unread: number
  other_user_id: string | null // the other person in a direct chat, to match presence news
  online: boolean // the other person has Parley open right now (D22)
  last_seen: string | null // when their app was last seen; null = unknown
  role: "admin" | "member" | null // groups: my role (D37). null in a direct chat
  left: boolean // I left this group or was removed: read-only (D37)
}

// One current member of a group, for the header and the side panel (D37)
export type GroupMember = {
  user_id: string
  name: string
  role: "admin" | "member"
}

// One message as the server sends it
export type ServerMessage = {
  id: string
  chat_id: string
  seq: number
  sender_id: string
  sender_name: string // shown above the bubble in a group
  client_msg_id: string
  body: string
  created_at: string
  // system = a group note, with data instead of text (D37); file = D38.
  // reaction, edit, delete = a change to another message, not one to show (D39)
  kind: "text" | "system" | "file" | "reaction" | "edit" | "delete"
  data: SystemData | FileData | EventData | null
  edited: boolean
  deleted: boolean
  reactions: Reactions
  state_seq: number // the number of the last change to this message: the higher copy wins
  target: ServerMessage | null // events: the changed message as it is now (null if I can't see it, D37)
}

// A change to a message has its own number but no bubble (D39)
export function isEvent(message: ServerMessage) {
  return message.kind === "reaction" || message.kind === "edit" || message.kind === "delete"
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
  members: MemberBookmarks[] // the current members' bookmarks, so ticks are right after a reload
  // Every number in this stretch is settled: it's in messages, or it's a change
  // those messages already show (D39). Null when the page settles nothing.
  low_seq: number | null
  high_seq: number | null
}

// What the server pushes down the live line (D19, D20)
export type LiveEvent =
  | { type: "hello"; data: { user_id: string; copy: string } } // copy: which backend copy picked up (D28)
  | { type: "message.new"; data: ServerMessage }
  | { type: "receipt"; data: { chat_id: string; user_id: string; delivered_up_to: number; read_up_to: number } }
  // A group's lowest bookmarks over its current members moved (D37)
  | { type: "group_receipt"; data: { chat_id: string; delivered_up_to: number; read_up_to: number } }
  | { type: "typing"; data: { chat_id: string; user_id: string; name: string } }
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
  senderName: string
  body: string
  createdAt: string
  status: "sending" | "waiting" | "failed" | "sent"
  kind: ServerMessage["kind"]
  data: ServerMessage["data"]
  edited: boolean
  deleted: boolean
  reactions: Reactions
  stateSeq: number
  // Only while my file is on its way
  progress?: number // 0 to 1
  localUrl?: string // the file from this device, shown until it's saved
}

// What a message that isn't saved yet starts with
export const NOT_CHANGED = { edited: false, deleted: false, reactions: {}, stateSeq: 0 }

export function fromServer(message: ServerMessage): Message {
  return {
    id: message.id,
    clientMsgId: message.client_msg_id,
    seq: message.seq,
    senderId: message.sender_id,
    senderName: message.sender_name,
    body: message.body,
    createdAt: message.created_at,
    status: "sent",
    kind: message.kind,
    data: message.data,
    edited: message.edited,
    deleted: message.deleted,
    reactions: message.reactions,
    stateSeq: message.state_seq,
  }
}

// Picks a tint from an id, so the same chat always gets the same color
const tints: Tint[] = ["teal", "purple", "yellow", "red"]

export function tintFor(id: string): Tint {
  let sum = 0
  for (const char of id) sum += char.charCodeAt(0)
  return tints[sum % tints.length]
}
