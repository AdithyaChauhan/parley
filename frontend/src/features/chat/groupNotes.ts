import { ApiError, isBusy, isUnreachable } from "@/lib/api"
import type { ChatSummary, FileData, GroupMember, Person, SystemData } from "./types"

// The server keeps a group note's facts (who did what to whom), and the app
// writes the words (D37), so "you" can be you on every screen.

// "Ana", or "You" / "you" when it's me
function who(person: Person, myId: string, start: boolean) {
  if (person.id !== myId) return person.name
  return start ? "You" : "you"
}

// "Ben", "Ben and Cara", "Ben, Cara and Dev"
function list(people: Person[], myId: string) {
  const names = people.map((person) => who(person, myId, false))
  if (names.length <= 1) return names.join("")
  return `${names.slice(0, -1).join(", ")} and ${names.at(-1)}`
}

// One note's words, like "Ana added Ben and Cara"
export function noteText(data: SystemData, myId: string) {
  const by = who(data.by, myId, true)
  const users = list(data.users ?? [], myId)
  switch (data.event) {
    case "created":
      return `${by} created the group "${data.name}"`
    case "added":
      return `${by} added ${users}`
    case "removed":
      return `${by} removed ${users}`
    case "left": {
      const left = `${by} left`
      if (!data.new_admin) return left
      // The last admin left, so the longest-standing member took over (D37)
      const admin = data.new_admin.id === myId ? "You're" : `${data.new_admin.name} is`
      return `${left}. ${admin} now an admin`
    }
    case "renamed":
      return `${by} changed the group name to "${data.name}"`
    case "made_admin":
      return `${by} made ${users} an admin`
  }
}

// The grey line under a chat's name in the list: the note's words, "Ana: hi" in a group, or just the text
// What the chat list says for a file (D38)
function fileLine(chat: ChatSummary, data: FileData, sender: string | null) {
  const line =
    data.category === "image" ? "📷 Photo" : data.category === "voice" ? "🎤 Voice message" : `📄 ${data.name}`
  return chat.kind === "group" && sender ? `${sender}: ${line}` : line
}

export function previewText(chat: ChatSummary, myId: string) {
  const last = chat.last_message
  if (!last) return "No messages yet"
  if (last.kind === "system" && last.data) return noteText(last.data as SystemData, myId)
  if (last.kind === "file" && last.data) return fileLine(chat, last.data as FileData, last.sender_name)
  if (chat.kind !== "group") return last.preview
  const sender = last.sender_id === myId ? "You" : last.sender_name
  return `${sender}: ${last.preview}`
}

// A group's header line: its members' names, me last as "You", like WhatsApp (D37)
export function memberNames(members: GroupMember[] | null, myId: string) {
  if (!members) return ""
  const others = members.filter((member) => member.user_id !== myId).map((member) => member.name)
  return [...others, ...(members.some((member) => member.user_id === myId) ? ["You"] : [])].join(", ")
}

// The server's answer, in words
export function groupError(error: unknown) {
  if (error instanceof ApiError) {
    const detail = (error.body as { detail?: unknown } | null)?.detail
    // 400, 403 and 404 carry a sentence written for people, like "No account with ben@example.com"
    if ([400, 403, 404].includes(error.status) && typeof detail === "string") return `${detail}.`
    if (error.status === 429) return "Slow down a moment."
  }
  if (isBusy(error)) return "Busy, try again in a moment."
  if (isUnreachable(error)) return "Can't reach Parley."
  return "Something went wrong. Try again."
}
