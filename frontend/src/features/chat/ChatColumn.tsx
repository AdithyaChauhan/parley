import { useEffect, useRef, useState } from "react"
import {
  Bell,
  BellOff,
  BellRing,
  LogOut,
  Plus,
  Search,
  Settings,
} from "lucide-react"
import { Avatar } from "@/components/Avatar"
import type { LiveStatus } from "@/lib/live"
import { pushState, turnOnPush, type PushState } from "@/lib/push"
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
  typing: Record<string, string> // chat id → who is typing there
  phoneVisible: boolean
  myName: string
  live: LiveStatus // my live line: green dot when online, else grey
  onLogout: () => void
}

// "Turn on notifications" in the gear menu (D26). The browser only asks on
// this click, never on page load. Hidden where pushes can't work (Incognito).
function NotificationsItem() {
  const [state, setState] = useState<PushState | null>(null) // null = still checking
  const [busy, setBusy] = useState(false)
  const [problem, setProblem] = useState<string | null>(null) // why the last try failed

  useEffect(() => {
    pushState().then(setState)
  }, [])

  async function turnOn() {
    setBusy(true)
    setProblem(null)
    try {
      setState(await turnOnPush())
    } catch (error) {
      // For example the server has no keys (503), or the browser's push service refused.
      setProblem(error instanceof Error ? error.message : "Couldn't turn them on")
      setState(await pushState())
    } finally {
      setBusy(false)
    }
  }

  if (state === null || state === "unsupported") return null
  const Icon = state === "on" ? BellRing : state === "blocked" ? BellOff : Bell
  return (
    <>
      <button
        type="button"
        onClick={turnOn}
        disabled={state !== "off" || busy}
        title={state === "blocked" ? "Allow notifications in the browser's site settings" : undefined}
        className="flex w-full items-center gap-2 rounded-md px-3 py-2 text-left text-sm hover:bg-row-selected disabled:hover:bg-transparent"
      >
        <Icon className="size-4 text-muted-foreground" />
        {busy
          ? "Waiting for the browser..."
          : state === "on"
            ? "Notifications on"
            : state === "blocked"
              ? "Notifications blocked"
              : "Turn on notifications"}
      </button>
      {problem && <p className="px-3 pb-2 text-xs text-destructive">{problem}</p>}
    </>
  )
}

// The left column: title, my profile, search box and the list of chats
export function ChatColumn({
  chats,
  loadFailed,
  openId,
  onSelect,
  onChatStarted,
  typing,
  phoneVisible,
  myName,
  live,
  onLogout,
}: ChatColumnProps) {
  const [search, setSearch] = useState("")
  const [menuOpen, setMenuOpen] = useState(false)
  const [newChatOpen, setNewChatOpen] = useState(false)
  const shown = (chats ?? []).filter((chat) => chat.name.toLowerCase().includes(search.trim().toLowerCase()))
  // The gear and its menu, so a tap inside them doesn't count as "outside"
  const menuRef = useRef<HTMLDivElement>(null)

  // While the gear menu is open: a tap or click anywhere else, or Esc, closes it
  useEffect(() => {
    if (!menuOpen) return
    function closeIfOutside(e: PointerEvent) {
      if (!menuRef.current?.contains(e.target as Node)) setMenuOpen(false)
    }
    function closeOnEsc(e: KeyboardEvent) {
      if (e.key === "Escape") setMenuOpen(false)
    }
    document.addEventListener("pointerdown", closeIfOutside)
    document.addEventListener("keydown", closeOnEsc)
    return () => {
      document.removeEventListener("pointerdown", closeIfOutside)
      document.removeEventListener("keydown", closeOnEsc)
    }
  }, [menuOpen])

  return (
    <section
      // 768-1023px: a narrower list, so the conversation keeps its room
      className={cn(
        "min-h-0 flex-1 flex-col px-4 md:w-70 md:flex-none lg:w-85",
        phoneVisible ? "flex" : "hidden md:flex",
      )}
    >
      {/* No header, even on a phone: the profile is the top of the column (D8) */}
      <div className="relative flex shrink-0 flex-col items-center pt-6 pb-4">
        {/* The gear opens a small menu with "Log out" */}
        <div ref={menuRef} className="absolute top-5 right-0">
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
            <div className="absolute top-full right-0 z-20 mt-1 w-56 rounded-lg bg-card p-1 shadow-lg ring-1 shadow-foreground/10 ring-border">
              <NotificationsItem />
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
        <Avatar name={myName} tint="teal" size="lg" status={live === "online" ? "online" : "offline"} />
        <p className="mt-2 text-name">{myName}</p>
        {/* Only while the live line is down: the list moves down a little then (D8) */}
        {live === "reconnecting" && <p className="mt-1 text-sm text-muted-foreground">Reconnecting...</p>}
      </div>

      <label className="flex h-12 shrink-0 items-center gap-2 rounded-lg bg-search px-5">
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search"
          // 16px on a phone: an iPhone zooms the whole page when you tap a smaller box
          className="min-w-0 flex-1 bg-transparent text-base outline-none placeholder:text-muted-foreground md:text-body"
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

      <div className="-mx-1 min-h-0 flex-1 overflow-y-auto overscroll-contain px-1 pb-4 scrollbar-thin">
        {shown.map((chat) => (
          <ChatRow
            key={chat.id}
            chat={chat}
            selected={chat.id === openId}
            typing={chat.id in typing}
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
