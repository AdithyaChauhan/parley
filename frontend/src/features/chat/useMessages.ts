import { useEffect, useRef, useState } from "react"
import { api } from "@/lib/api"
import { fromServer, type Message, type MessagePage, type ServerMessage } from "./types"

// Numbered messages in order; ones still waiting for a number stay at the end
function bySeq(a: Message, b: Message) {
  return (a.seq ?? Number.MAX_SAFE_INTEGER) - (b.seq ?? Number.MAX_SAFE_INTEGER)
}

// The messages of one open chat, oldest at the top.
// Loads the newest 30, loads older ones on request, and sends with retry.
// onSent tells the chat list, so the chat moves to the top with the new preview.
export function useMessages(chatId: string, myId: string, onSent: (message: ServerMessage) => void) {
  const [messages, setMessages] = useState<Message[]>([])
  const [hasMore, setHasMore] = useState(false)
  const [loading, setLoading] = useState(true)
  const [failed, setFailed] = useState(false)
  const loadingOlder = useRef(false) // so fast scrolling doesn't ask for the same page twice

  // The newest page. The server sends it newest first, so flip it.
  useEffect(() => {
    let ignore = false // the chat changed before the answer came: drop it
    api<MessagePage>(`/chats/${chatId}/messages`)
      .then((page) => {
        if (ignore) return
        setMessages(page.messages.map(fromServer).reverse())
        setHasMore(page.has_more)
      })
      .catch(() => !ignore && setFailed(true))
      .finally(() => !ignore && setLoading(false))
    return () => {
      ignore = true
    }
  }, [chatId])

  // The 30 just above the oldest numbered message on screen
  async function loadOlder() {
    const oldest = messages.find((message) => message.seq !== null)
    if (!hasMore || !oldest || loadingOlder.current) return

    loadingOlder.current = true
    try {
      const page = await api<MessagePage>(`/chats/${chatId}/messages?before=${oldest.seq}`)
      setMessages((current) => [...page.messages.map(fromServer).reverse(), ...current])
      setHasMore(page.has_more)
    } catch {
      // Nothing changes. Scrolling to the top again tries again.
    } finally {
      loadingOlder.current = false
    }
  }

  function setStatus(clientMsgId: string, status: Message["status"]) {
    setMessages((current) =>
      current.map((message) => (message.clientMsgId === clientMsgId ? { ...message, status } : message)),
    )
  }

  // Sends one message. A retry calls this again with the SAME clientMsgId,
  // so if the first try did reach the server, it answers with that copy (D9, D18).
  async function deliver(clientMsgId: string, body: string) {
    setStatus(clientMsgId, "sending")
    try {
      const saved = await api<ServerMessage>(`/chats/${chatId}/messages`, {
        method: "POST",
        body: { client_msg_id: clientMsgId, body },
      })
      // Swap our copy for the server's, which has its number
      setMessages((current) =>
        current.map((message) => (message.clientMsgId === clientMsgId ? fromServer(saved) : message)).sort(bySeq),
      )
      onSent(saved)
    } catch {
      setStatus(clientMsgId, "failed")
    }
  }

  // Shows the message at once, then sends it
  function send(body: string) {
    const clientMsgId = crypto.randomUUID() // a fresh ID for each new message (D9)
    const message: Message = {
      clientMsgId,
      seq: null,
      senderId: myId,
      body,
      createdAt: new Date().toISOString(),
      status: "sending",
    }
    setMessages((current) => [...current, message])
    deliver(clientMsgId, body)
  }

  function retry(message: Message) {
    deliver(message.clientMsgId, message.body)
  }

  return { messages, hasMore, loading, failed, loadOlder, send, retry }
}
