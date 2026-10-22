import { useRef, useState } from "react"
import { api, isUnreachable } from "@/lib/api"
import { announce, useLiveEvents } from "@/lib/live"
import type { Message, ServerMessage } from "./types"

// My messages that aren't saved yet, per chat, in the order I wrote them (D21).
// Every send goes through here, one at a time per chat, so a new message never
// overtakes an older one. It lives in ChatScreen, above the Conversation, so it
// keeps sending after you switch chats, and a "Not sent" message is still there when you come back.
//   - No answer (offline, or the server is down): the message waits, with
//     everything after it, until the line is back. Then they go out in order.
//   - A real refusal (like 422): "Not sent, tap to retry", and the next one goes on.
// Each message keeps its clientMsgId for every try, so if one did get through
// before the drop, the server hands back that first copy instead of a double (D18).
export function useOutbox(myId: string) {
  const [unsent, setUnsent] = useState<Record<string, Message[]>>({})
  // The same lists, readable at once inside a running send (state only updates on the next render)
  const lists = useRef<Record<string, Message[]>>({})
  // Chats whose queue is being sent right now
  const busy = useRef(new Set<string>())

  function update(chatId: string, change: (list: Message[]) => Message[]) {
    lists.current = { ...lists.current, [chatId]: change(lists.current[chatId] ?? []) }
    setUnsent(lists.current)
  }

  // Sends this chat's queue, oldest first, one at a time, until it's empty or the line is down
  async function sendQueue(chatId: string) {
    if (busy.current.has(chatId)) return // already going: it will reach the new ones too
    busy.current.add(chatId)
    try {
      while (true) {
        const next = lists.current[chatId]?.find((m) => m.status === "sending" || m.status === "waiting")
        if (!next) return
        const mark = (status: Message["status"]) =>
          update(chatId, (list) => list.map((m) => (m.clientMsgId === next.clientMsgId ? { ...m, status } : m)))

        mark("sending")
        try {
          const reply = await api<ServerMessage>(`/chats/${chatId}/messages`, {
            method: "POST",
            body: { client_msg_id: next.clientMsgId, body: next.body },
          })
          update(chatId, (list) => list.filter((m) => m.clientMsgId !== next.clientMsgId))
          // The reply is a saved message, like a pushed one, so it goes in the same way:
          // the chat list moves, and a skipped number starts a catch-up (D21)
          announce({ type: "message.new", data: reply })
        } catch (error) {
          if (isUnreachable(error)) {
            // Offline: this one and everything after it wait for the line
            update(chatId, (list) => list.map((m) => (m.status === "failed" ? m : { ...m, status: "waiting" })))
            return
          }
          mark("failed")
        }
      }
    } finally {
      busy.current.delete(chatId)
    }
  }

  // Shows the message at once, then sends it in its turn
  function send(chatId: string, body: string) {
    const message: Message = {
      id: null,
      clientMsgId: crypto.randomUUID(), // a fresh ID for each new message (D9)
      seq: null,
      senderId: myId,
      body,
      createdAt: new Date().toISOString(),
      status: "sending",
    }
    update(chatId, (list) => [...list, message])
    sendQueue(chatId)
  }

  // "Not sent, tap to retry": back in the queue, with the SAME clientMsgId
  function retry(chatId: string, message: Message) {
    update(chatId, (list) => list.map((m) => (m.clientMsgId === message.clientMsgId ? { ...m, status: "sending" } : m)))
    sendQueue(chatId)
  }

  // On the line again: every chat's waiting messages go out, in order (D21)
  useLiveEvents((event) => {
    if (event.type !== "hello") return
    for (const chatId of Object.keys(lists.current)) sendQueue(chatId)
  })

  return { unsent, send, retry }
}
