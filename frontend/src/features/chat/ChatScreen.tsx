import { useState } from "react"
import { chats as fakeChats, type Chat, type Message } from "@/data/fake"
import { ChatColumn } from "./ChatColumn"
import { Conversation } from "./Conversation"
import { IconRail } from "./IconRail"
import { SidePanel } from "./SidePanel"

// On a phone only one column shows at a time
type PhoneView = "list" | "chat" | "panel"

// "11:24 AM"
function timeNow() {
  return new Date().toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" })
}

// The whole main screen. It holds all the state; the columns only show it.
export function ChatScreen() {
  const [chats, setChats] = useState<Chat[]>(fakeChats)
  const [openId, setOpenId] = useState(fakeChats[0].id)
  // Open on wide screens (1280px and up). Folded on smaller laptops so the conversation keeps its room
  const [panelOpen, setPanelOpen] = useState(() => window.innerWidth >= 1280)
  const [phoneView, setPhoneView] = useState<PhoneView>("list")

  const openChat = chats.find((chat) => chat.id === openId) ?? chats[0]

  function selectChat(id: string) {
    setOpenId(id)
    setPhoneView("chat")
    // Opening a chat clears its unread count
    setChats((all) => all.map((chat) => (chat.id === id ? { ...chat, unread: 0 } : chat)))
  }

  // Fake send: add my message with one grey tick. No backend yet (T14).
  function sendMessage(text: string) {
    const message: Message = {
      id: crypto.randomUUID(), // the sender's app makes the ID (D9)
      senderId: "me",
      text,
      time: timeNow(),
      tick: "sent",
    }
    setChats((all) =>
      all.map((chat) =>
        chat.id === openId ? { ...chat, day: undefined, messages: [...chat.messages, message] } : chat,
      ),
    )
  }

  return (
    // Fills the whole browser window, with no outer frame (D8)
    <div className="flex h-svh w-full flex-col overflow-hidden bg-card md:flex-row">
      <IconRail />
      <ChatColumn
        chats={chats}
        openId={openChat.id}
        onSelect={selectChat}
        phoneVisible={phoneView === "list"}
      />
      <Conversation
        chat={openChat}
        onSend={sendMessage}
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
    </div>
  )
}
