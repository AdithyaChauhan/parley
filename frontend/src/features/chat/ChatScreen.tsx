import { useEffect, useState } from "react"
import { useAuth, type User } from "@/features/auth/useAuth"
import { api } from "@/lib/api"
import { reportDelivered, useLiveConnection, useLiveEvents } from "@/lib/live"
import { ChatColumn } from "./ChatColumn"
import { Conversation } from "./Conversation"
import { IconRail } from "./IconRail"
import { SidePanel } from "./SidePanel"
import type { ChatSummary, Message, ServerMessage } from "./types"
import type { UpdateUnsent } from "./useMessages"

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
  // My unsaved messages per chat ("sending" or "Not sent"). Kept here, above the
  // Conversation, so they're still there after switching chats and back.
  const [unsent, setUnsent] = useState<Record<string, Message[]>>({})
  // This screen only shows while logged in, so the line opens on log-in and closes on log-out.
  const connected = useLiveConnection()

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

  const openChat = chats?.find((chat) => chat.id === openId) ?? null

  // The unread count stays until read bookmarks arrive (T18)
  function selectChat(id: string) {
    setOpenId(id)
    setPhoneView("chat")
  }

  // From the "+" box. If we already had this chat, just open it.
  function chatStarted(chat: ChatSummary) {
    setChats((all) => {
      const list = all ?? []
      return list.some((c) => c.id === chat.id) ? list : [chat, ...list]
    })
    selectChat(chat.id)
  }

  const updateUnsent: UpdateUnsent = (chatId, update) =>
    setUnsent((all) => ({ ...all, [chatId]: update(all[chatId] ?? []) }))

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
      // Their new message adds 1, unless the chat is open on screen.
      let unread = chat.unread
      if (message.sender_id === user.id) unread = 0
      else if (isNew && chat.id !== openId) unread += 1
      return [{ ...chat, last_message: lastMessage, unread }, ...all.filter((c) => c.id !== chat.id)]
    })
  }

  // A new message pushed live (D20). It's on this device now, so tell the server.
  // A chat I don't have yet (someone just started it with me): load the list again.
  useLiveEvents((event) => {
    if (event.type !== "message.new") return
    const message = event.data
    reportDelivered(message.chat_id, message.seq)
    if (!chats) return // the list is still loading, and will include it
    if (chats.some((chat) => chat.id === message.chat_id)) {
      messageArrived(message)
    } else {
      api<ChatSummary[]>("/chats")
        .then((list) => {
          setChats(list)
          reportListDelivered(list)
        })
        .catch(() => {})
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
        phoneVisible={phoneView === "list"}
        myName={user.name}
        connected={connected}
        onLogout={logout}
      />
      {openChat ? (
        <>
          {/* key: a new chat gets a fresh Conversation, with its own messages */}
          <Conversation
            key={openChat.id}
            chat={openChat}
            myId={user.id}
            unsent={unsent[openChat.id] ?? []}
            updateUnsent={updateUnsent}
            onSent={messageArrived}
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
