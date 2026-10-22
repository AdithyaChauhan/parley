import { useEffect, useRef, useState } from "react"
import { api } from "@/lib/api"
import { reportDelivered, useLiveEvents } from "@/lib/live"
import { fromServer, type Message, type MessagePage, type ServerMessage } from "./types"

// Changes one chat's list of my unsaved messages ("sending" or "Not sent").
// The lists live above the Conversation, in ChatScreen, so a "Not sent"
// message is still there after you switch chats and come back.
export type UpdateUnsent = (chatId: string, update: (unsent: Message[]) => Message[]) => void

// Both lists together, each saved message once (matched by id), in number order
function merge(a: Message[], b: Message[]) {
  const byId = new Map([...a, ...b].map((message) => [message.id, message]))
  return [...byId.values()].sort((x, y) => (x.seq ?? 0) - (y.seq ?? 0))
}

// The messages of one open chat, oldest at the top: saved ones by number,
// then my unsaved ones. Loads the newest 30, loads older ones on request,
// sends with retry, and takes in new messages and ticks pushed live (D20).
// onSent tells the chat list, so the chat moves to the top with the new preview.
export function useMessages(
  chatId: string,
  myId: string,
  unsent: Message[],
  updateUnsent: UpdateUnsent,
  onSent: (message: ServerMessage) => void,
) {
  const [saved, setSaved] = useState<Message[]>([])
  // The other person's bookmarks: my messages up to "delivered" get grey ✓✓, up to "read" teal ✓✓
  const [theirDelivered, setTheirDelivered] = useState(0)
  const [theirRead, setTheirRead] = useState(0)
  const [hasMore, setHasMore] = useState(false)
  const [loading, setLoading] = useState(true)
  const [failed, setFailed] = useState(false)
  const loadingOlder = useRef(false) // so fast scrolling doesn't ask for the same page twice

  const messages = [...saved, ...unsent]
  // The highest number here, which is what a "read" reports. 0 = no messages yet.
  const newestSeq = saved.at(-1)?.seq ?? 0

  // A saved message for this chat: my send's reply, or one pushed live.
  // Never twice: the merge matches by id, and my own unsent copy (same clientMsgId) is taken out.
  function addSaved(message: ServerMessage) {
    if (message.sender_id === myId) {
      updateUnsent(chatId, (list) => list.filter((m) => m.clientMsgId !== message.client_msg_id))
    }
    setSaved((current) => merge(current, [fromServer(message)]))
  }

  // The newest page. The server sends it newest first; merge sorts it.
  // Merged, not replaced: a message pushed while this loads must not be lost.
  useEffect(() => {
    let ignore = false // the chat changed before the answer came: drop it
    api<MessagePage>(`/chats/${chatId}/messages`)
      .then((page) => {
        if (ignore) return
        setSaved((current) => merge(page.messages.map(fromServer), current))
        setHasMore(page.has_more)
        const them = page.members.find((member) => member.user_id !== myId)
        setTheirDelivered((current) => Math.max(current, them?.delivered_up_to ?? 0))
        setTheirRead((current) => Math.max(current, them?.read_up_to ?? 0))
        if (page.messages.length > 0) reportDelivered(chatId, page.messages[0].seq)
      })
      .catch(() => !ignore && setFailed(true))
      .finally(() => !ignore && setLoading(false))
    return () => {
      ignore = true
    }
  }, [chatId, myId])

  useLiveEvents((event) => {
    if (event.type === "message.new" && event.data.chat_id === chatId) {
      addSaved(event.data)
    }
    // The other person got or read more of my messages: redraw the ticks
    if (event.type === "receipt" && event.data.chat_id === chatId && event.data.user_id !== myId) {
      const { delivered_up_to: deliveredUpTo, read_up_to: readUpTo } = event.data
      setTheirDelivered((current) => Math.max(current, deliveredUpTo))
      setTheirRead((current) => Math.max(current, readUpTo))
    }
  })

  // The 30 just above the oldest message on screen
  async function loadOlder() {
    const oldest = saved[0]
    if (!hasMore || !oldest || loadingOlder.current) return

    loadingOlder.current = true
    try {
      const page = await api<MessagePage>(`/chats/${chatId}/messages?before=${oldest.seq}`)
      setSaved((current) => merge(page.messages.map(fromServer), current))
      setHasMore(page.has_more)
    } catch {
      // Nothing changes. Scrolling to the top again tries again.
    } finally {
      loadingOlder.current = false
    }
  }

  function setStatus(clientMsgId: string, status: Message["status"]) {
    updateUnsent(chatId, (list) =>
      list.map((message) => (message.clientMsgId === clientMsgId ? { ...message, status } : message)),
    )
  }

  // Sends one message. A retry calls this again with the SAME clientMsgId,
  // so if the first try did reach the server, it answers with that copy (D9, D18).
  async function deliver(message: Message) {
    setStatus(message.clientMsgId, "sending")
    try {
      const reply = await api<ServerMessage>(`/chats/${chatId}/messages`, {
        method: "POST",
        body: { client_msg_id: message.clientMsgId, body: message.body },
      })
      addSaved(reply)
      onSent(reply)
    } catch {
      setStatus(message.clientMsgId, "failed")
    }
  }

  // Shows the message at once, then sends it
  function send(body: string) {
    const message: Message = {
      id: null,
      clientMsgId: crypto.randomUUID(), // a fresh ID for each new message (D9)
      seq: null,
      senderId: myId,
      body,
      createdAt: new Date().toISOString(),
      status: "sending",
    }
    updateUnsent(chatId, (list) => [...list, message])
    deliver(message)
  }

  return { messages, newestSeq, theirDelivered, theirRead, hasMore, loading, failed, loadOlder, send, retry: deliver }
}
