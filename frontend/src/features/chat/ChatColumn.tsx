import { useState } from "react"
import { ChevronDown, ChevronLeft, EllipsisVertical, LogOut, Plus, Search, Settings } from "lucide-react"
import { Avatar } from "@/components/Avatar"
import { cn } from "@/lib/utils"
import { ChatRow } from "./ChatRow"
import { NewChatBox } from "./NewChatBox"
import type { ChatSummary } from "./types"

type ChatColumnProps = {
  chats: ChatSummary[] | null // null = still loading
  loadFailed: boolean
  openId: string | null
  onSelect: (id: string) => void
  onChatStarted: (chat: ChatSummary) => void
  phoneVisible: boolean
  myName: string
  connected: boolean // my live line is open: green dot, else grey
  onLogout: () => void
}

// The left column: title, my profile, search box and the list of chats
export function ChatColumn({
  chats,
  loadFailed,
  openId,
  onSelect,
  onChatStarted,
  phoneVisible,
  myName,
  connected,
  onLogout,
}: ChatColumnProps) {
  const [search, setSearch] = useState("")
  const [menuOpen, setMenuOpen] = useState(false)
  const [newChatOpen, setNewChatOpen] = useState(false)
  const shown = (chats ?? []).filter((chat) => chat.name.toLowerCase().includes(search.trim().toLowerCase()))

  return (
    <section
      className={cn(
        "min-h-0 flex-1 flex-col px-4 md:w-85 md:flex-none",
        phoneVisible ? "flex" : "hidden md:flex",
      )}
    >
      {/* Phone only. On desktop the profile is the top of the column. */}
      <header className="flex h-20 shrink-0 items-center gap-4 border-b pt-4 md:hidden">
        <button
          type="button"
          aria-label="Back"
          className="flex size-10 items-center justify-center rounded-lg bg-row-selected text-muted-foreground"
        >
          <ChevronLeft className="size-4" />
        </button>
        <h1 className="text-header">Chat</h1>
      </header>

      <div className="relative flex shrink-0 flex-col items-center pt-4 pb-4 md:pt-6">
        {/* The gear opens a small menu with "Log out" */}
        <div className="absolute top-3 right-0 md:top-5">
          <button
            type="button"
            onClick={() => setMenuOpen((open) => !open)}
            aria-label="Settings"
            aria-expanded={menuOpen}
            className="flex size-8 items-center justify-center rounded-lg text-rail-icon hover:text-muted-foreground"
          >
            <Settings className="size-5" />
          </button>
          {menuOpen && (
            <div className="absolute top-full right-0 z-20 mt-1 w-36 rounded-lg bg-card p-1 shadow-lg ring-1 shadow-foreground/10 ring-border">
              <button
                type="button"
                onClick={onLogout}
                className="flex w-full items-center gap-2 rounded-md px-3 py-2 text-left text-sm hover:bg-row-selected"
              >
                <LogOut className="size-4 text-muted-foreground" />
                Log out
              </button>
            </div>
          )}
        </div>
        <Avatar name={myName} tint="teal" size="lg" status={connected ? "online" : "offline"} />
        <p className="mt-2 text-name">{myName}</p>
        <button
          type="button"
          className="mt-2 flex items-center gap-1.5 rounded-md bg-status-pill px-3 py-0.5 text-sm text-primary"
        >
          available
          <ChevronDown className="size-3.5" />
        </button>
      </div>

      <label className="flex h-12 shrink-0 items-center gap-2 rounded-lg bg-search px-5">
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search"
          className="min-w-0 flex-1 bg-transparent outline-none placeholder:text-muted-foreground"
        />
        <Search className="size-4 text-muted-foreground" />
      </label>

      <div className="mt-4 mb-2 flex shrink-0 items-center justify-between">
        <h2>Last chats</h2>
        <div className="relative flex items-center gap-2">
          <button
            type="button"
            onClick={() => setNewChatOpen((open) => !open)}
            aria-label="New chat"
            aria-expanded={newChatOpen}
            className="flex size-8 items-center justify-center rounded-lg bg-accent text-primary"
          >
            <Plus className="size-4" />
          </button>
          <button type="button" aria-label="More" className="text-muted-foreground">
            <EllipsisVertical className="size-4" />
          </button>
          {newChatOpen && (
            <NewChatBox
              onStarted={(chat) => {
                setNewChatOpen(false)
                onChatStarted(chat)
              }}
              onClose={() => setNewChatOpen(false)}
            />
          )}
        </div>
      </div>

      <div className="-mx-1 min-h-0 flex-1 overflow-y-auto px-1 pb-4 scrollbar-thin">
        {shown.map((chat) => (
          <ChatRow
            key={chat.id}
            chat={chat}
            selected={chat.id === openId}
            onSelect={() => onSelect(chat.id)}
          />
        ))}
        {loadFailed && <p className="px-4 py-6 text-sm text-muted-foreground">Can't reach Parley. Reload to try again.</p>}
        {!chats && !loadFailed && <p className="px-4 py-6 text-sm text-muted-foreground">Loading chats...</p>}
        {chats?.length === 0 && (
          <div className="flex flex-col items-center gap-3 px-4 py-10 text-center">
            <p className="text-muted-foreground">Start your first chat</p>
            <button
              type="button"
              onClick={() => setNewChatOpen(true)}
              aria-label="New chat"
              className="flex size-10 items-center justify-center rounded-lg bg-accent text-primary"
            >
              <Plus className="size-5" />
            </button>
          </div>
        )}
        {chats && chats.length > 0 && shown.length === 0 && (
          <p className="px-4 py-6 text-sm text-muted-foreground">No chats found</p>
        )}
      </div>
    </section>
  )
}
