import { useEffect, useState } from "react"
import { useAuth, type User } from "@/features/auth/useAuth"
import { api } from "@/lib/api"
import { useLiveConnection } from "@/lib/live"
import { ChatColumn } from "./ChatColumn"
import { Conversation } from "./Conversation"
import { IconRail } from "./IconRail"
import { SidePanel } from "./SidePanel"
import type { ChatSummary, ServerMessage } from "./types"

// On a phone only one column shows at a time
type PhoneView = "list" | "chat" | "panel"

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

  // My message was saved: its chat moves to the top with the new preview.
  // Sending also counts as reading everything above it (T14), so unread goes to 0, like on the server.
  function messageSent(message: ServerMessage) {
    setChats((all) => {
      const chat = all?.find((c) => c.id === message.chat_id)
      if (!all || !chat) return all
      const lastMessage = { seq: message.seq, preview: message.body, created_at: message.created_at }
      return [{ ...chat, last_message: lastMessage, unread: 0 }, ...all.filter((c) => c.id !== chat.id)]
    })
  }

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
            onSent={messageSent}
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
