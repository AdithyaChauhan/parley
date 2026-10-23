import { useEffect, useEffectEvent, useState } from "react"
import { useAuth, type User } from "@/features/auth/useAuth"
import { api } from "@/lib/api"
import { reportDelivered, useLiveConnection, useLiveEvents } from "@/lib/live"
import { ChatColumn } from "./ChatColumn"
import { Conversation } from "./Conversation"
import { IconRail } from "./IconRail"
import { SidePanel } from "./SidePanel"
import type { ChatSummary, ServerMessage } from "./types"
import { useOutbox } from "./useOutbox"
import { useTyping } from "./useTyping"

// On a phone only one column shows at a time
type PhoneView = "list" | "chat" | "panel"

// The chat list shows each chat's newest message, so it's on this device now (D20)
function reportListDelivered(list: ChatSummary[]) {
  for (const chat of list) {
    if (chat.last_message) reportDelivered(chat.id, chat.last_message.seq)
  }
}

// The whole main screen. It holds the chat list and which chat is open;
// the open chat's messages live in Conversation (useMessages).
export function ChatScreen({ user }: { user: User }) {
  const { logout } = useAuth()
  const [chats, setChats] = useState<ChatSummary[] | null>(null) // null = still loading
  const [loadFailed, setLoadFailed] = useState(false)
  const [openId, setOpenId] = useState<string | null>(null)
  // Open on wide screens (1280px and up). Folded on smaller laptops so the conversation keeps its room
  const [panelOpen, setPanelOpen] = useState(() => window.innerWidth >= 1280)
  const [phoneView, setPhoneView] = useState<PhoneView>("list")
  // My unsaved messages per chat, sent one at a time, in order (D21)
  const outbox = useOutbox(user.id)
  // This screen only shows while logged in, so the line opens on log-in and closes on log-out.
  const live = useLiveConnection()
  // Who is typing in which chat, for the chat list and the open conversation
  const typing = useTyping()

  // My real chats, newest activity first. The first one opens on its own.
  useEffect(() => {
    let ignore = false
    api<ChatSummary[]>("/chats")
      .then((list) => {
        if (ignore) return
        setChats(list)
        setOpenId((current) => current ?? list[0]?.id ?? null)
        reportListDelivered(list)
      })
      .catch(() => !ignore && setLoadFailed(true))
    return () => {
      ignore = true
    }
  }, [])

  // The chat list again, quietly (a failure leaves the old list up): a chat I
  // don't have yet, or back on the line, when previews, unread counts and even
  // whole chats may have changed while it was down (D21)
  function reloadChats() {
    api<ChatSummary[]>("/chats")
      .then((list) => {
        setChats(list)
        setLoadFailed(false)
        setOpenId((current) => current ?? list[0]?.id ?? null)
        reportListDelivered(list)
      })
      .catch(() => {})
  }

  const openChat = chats?.find((chat) => chat.id === openId) ?? null

  // Opening a chat doesn't clear its unread count by itself: the Conversation
  // does that (markRead) once the messages are really on screen (D20).
  function selectChat(id: string) {
    setOpenId(id)
    setPhoneView("chat")
  }

  // The open chat sent "read": nothing in it is unread any more
  function markRead(chatId: string) {
    setChats((all) => {
      if (!all?.some((chat) => chat.id === chatId && chat.unread > 0)) return all // already 0
      return all.map((chat) => (chat.id === chatId ? { ...chat, unread: 0 } : chat))
    })
  }

  // My read bookmark moved, maybe in another tab (D20). Unread is always the
  // newest number minus it. A "delivered" or late receipt never raises it.
  function myReadMoved(chatId: string, readUpTo: number) {
    setChats(
      (all) =>
        all &&
        all.map((chat) => {
          if (chat.id !== chatId) return chat
          const unread = Math.max(0, (chat.last_message?.seq ?? 0) - readUpTo)
          return unread < chat.unread ? { ...chat, unread } : chat
        }),
    )
  }

  // Someone I share a chat with came online or went offline (D22)
  function presenceChanged(userId: string, online: boolean, lastSeen: string | null) {
    setChats(
      (all) =>
        all && all.map((chat) => (chat.other_user_id === userId ? { ...chat, online, last_seen: lastSeen } : chat)),
    )
  }

  // While a chat is open, check everyone's online status again every 60 s.
  // A crashed tab never says goodbye, so no "offline" news ever comes for it:
  // only its time running out on the server tells (D22).
  const recheckPresence = useEffectEvent(() => reloadChats())
  useEffect(() => {
    if (!openId) return
    const timer = window.setInterval(recheckPresence, 60_000)
    return () => clearInterval(timer)
  }, [openId])

  // From the "+" box. If we already had this chat, just open it.
  function chatStarted(chat: ChatSummary) {
    setChats((all) => {
      const list = all ?? []
      return list.some((c) => c.id === chat.id) ? list : [chat, ...list]
    })
    selectChat(chat.id)
  }

  // A saved message reached this tab: my send's reply, or one pushed live.
  // Its chat moves to the top. My own message arrives twice (the reply and the
  // push), so only a newer number changes the preview.
  function messageArrived(message: ServerMessage) {
    setChats((all) => {
      const chat = all?.find((c) => c.id === message.chat_id)
      if (!all || !chat) return all
      const isNew = message.seq > (chat.last_message?.seq ?? 0)
      const lastMessage = isNew
        ? { seq: message.seq, preview: message.body, created_at: message.created_at }
        : chat.last_message
      // Sending counts as reading everything above it (T14), like on the server.
      // Their new message adds 1. If the chat is open and you're looking, the
      // Conversation sends "read" and sets it back to 0 before the screen is drawn.
      let unread = chat.unread
      if (message.sender_id === user.id) unread = 0
      else if (isNew) unread += 1
      return [{ ...chat, last_message: lastMessage, unread }, ...all.filter((c) => c.id !== chat.id)]
    })
  }

  // A new message pushed live (D20). It's on this device now, so tell the server.
  // A chat I don't have yet (someone just started it with me): load the list again.
  // A receipt about me: I read something, here or in another tab.
  // A hello: on the line again, so catch up on the list (D21).
  // Presence: someone's green dot turns on or off.
  useLiveEvents((event) => {
    if (event.type === "hello") {
      reloadChats()
      return
    }
    if (event.type === "presence") {
      presenceChanged(event.data.user_id, event.data.online, event.data.last_seen)
      return
    }
    if (event.type === "receipt" && event.data.user_id === user.id) {
      myReadMoved(event.data.chat_id, event.data.read_up_to)
      return
    }
    if (event.type !== "message.new") return
    const message = event.data
    reportDelivered(message.chat_id, message.seq)
    if (!chats) return // the list is still loading, and will include it
    if (chats.some((chat) => chat.id === message.chat_id)) {
      messageArrived(message)
    } else {
      reloadChats()
    }
  })

  return (
    // Fills the whole browser window, with no outer frame (D8)
    <div className="flex h-svh w-full flex-col overflow-hidden bg-card md:flex-row">
      <IconRail myName={user.name} />
      <ChatColumn
        chats={chats}
        loadFailed={loadFailed}
        openId={openId}
        onSelect={selectChat}
        onChatStarted={chatStarted}
        typing={typing}
        phoneVisible={phoneView === "list"}
        myName={user.name}
        live={live}
        onLogout={logout}
      />
      {openChat ? (
        <>
          {/* key: a new chat gets a fresh Conversation, with its own messages */}
          <Conversation
            key={openChat.id}
            chat={openChat}
            myId={user.id}
            unsent={outbox.unsent[openChat.id] ?? []}
            onSend={(body) => outbox.send(openChat.id, body)}
            onRetry={(message) => outbox.retry(openChat.id, message)}
            typing={openChat.id in typing}
            onRead={() => markRead(openChat.id)}
            onBack={() => setPhoneView("list")}
            onOpenPanel={() => setPhoneView("panel")}
            phoneVisible={phoneView === "chat"}
          />
          <SidePanel
            chat={openChat}
            open={panelOpen}
            onToggle={() => setPanelOpen((open) => !open)}
            onBack={() => setPhoneView("chat")}
            phoneVisible={phoneView === "panel"}
          />
        </>
      ) : (
        <section className="hidden min-w-0 flex-1 items-center justify-center bg-conversation text-muted-foreground md:my-4 md:mr-4 md:flex md:rounded-panel">
          {chats ? "Pick a chat, or start one with +" : ""}
        </section>
      )}
    </div>
  )
}
