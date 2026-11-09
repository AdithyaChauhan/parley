import { useEffect, useEffectEvent, useLayoutEffect, useRef, useState, type DragEvent } from "react"
import { ArrowLeft, FolderUp, Search } from "lucide-react"
import { Avatar } from "@/components/Avatar"
import { api } from "@/lib/api"
import { prepareFile, type PreparedFile } from "@/lib/files"
import { keep, type Kept } from "@/lib/localCopy"
import { reportRead, sendTyping, windowInFront } from "@/lib/live"
import { cn } from "@/lib/utils"
import { EditBox, MessageBox } from "./MessageBox"
import { MessageMenu, type OpenMenu } from "./MessageMenu"
import { groupError, memberNames } from "./groupNotes"
import { MessageBubble, SystemNote, type BubbleActions } from "./MessageBubble"
import { ChatSearch } from "./SearchResults"
import { lastSeenText } from "./time"
import {
  REACTIONS,
  tintFor,
  type ChatSummary,
  type GroupMember,
  type Message,
  type NarrowView,
  type ServerMessage,
} from "./types"
import { useMessages } from "./useMessages"
import type { HistoryLoad } from "./useSearch"
import type { Typist } from "./useTyping"

// Scrolled up less than this counts as "at the bottom": the newest message is on screen
const NEAR_BOTTOM_PX = 80
// The server checks these again; the app only hides what would be refused (D39)
const EDIT_FOR_MS = 15 * 60_000
const DELETE_FOR_MS = 60 * 60_000
// How often "can I still edit this?" is looked at again
const CLOCK_EVERY_MS = 30_000

// How much of the list is below what you can see, in pixels
function hiddenBelow(list: HTMLElement) {
  return list.scrollHeight - list.scrollTop - list.clientHeight
}

type ConversationProps = {
  chat: ChatSummary
  myId: string
  unsent: Message[] // my messages in this chat that aren't saved yet (the outbox)
  onSend: (body: string) => void // into the outbox
  onRetry: (message: Message) => void // "Not sent, tap to retry"
  onSendFile: (file: PreparedFile) => void // into the outbox
  onCancel: (message: Message) => void // stops a file on its way
  typing: Typist | undefined // someone is typing here
  members: GroupMember[] | null // a group's current members (null for a direct chat, or while loading)
  onRead: () => void // I've seen everything here: the chat list sets unread to 0
  onBack: () => void
  onOpenPanel: () => void // below 1280px: the side panel takes this conversation's place
  view: NarrowView // below 1280px: what has the shared spot
  listChecks: number // goes up each time the chat list re-checks the server
  lineDown: boolean // the live line dropped or failed: nothing is pushed now
  jump: number | null // a tapped search result: open at this message number (D40)
  onJumped: () => void // handled
  history: HistoryLoad // "Load all my history"
  onOpenHit: (hit: Kept) => void // a search result in this chat was tapped
}

// The middle panel: who you're talking to, the messages, and the message box
export function Conversation({
  chat,
  myId,
  unsent,
  onSend,
  onRetry,
  onSendFile,
  onCancel,
  typing,
  members,
  onRead,
  onBack,
  onOpenPanel,
  view,
  listChecks,
  lineDown,
  jump,
  onJumped,
  history,
  onOpenHit,
}: ConversationProps) {
  const { messages, gapFreeSeq, theirDelivered, theirRead, hasMore, loading, failed, loadOlder, loadBackTo, applyChange } =
    useMessages(chat.id, myId, unsent, { seq: chat.last_message?.seq ?? 0, checks: listChecks, lineDown })
  const listRef = useRef<HTMLDivElement>(null)
  // How far from the bottom you were when older messages were asked for
  const fromBottom = useRef<number | null>(null)
  // You're at the newest message, so the list keeps the bottom in view
  const atBottom = useRef(true)
  // The search inside this chat. Its words stay after a tap, so you can look at the next result.
  const [searchOpen, setSearchOpen] = useState(false)
  const [searchQuery, setSearchQuery] = useState("")
  // A search result that's still loading: go there when its page arrives
  const goingTo = useRef<number | null>(null)

  // A short note above the message box: a file that can't be sent, or a recording tip
  const [hint, setHint] = useState("")
  const hintTimer = useRef<number | undefined>(undefined)
  // Files are being dragged over the conversation. Counted, because moving over
  // each child fires its own enter and leave.
  const dragDepth = useRef(0)
  const [dragging, setDragging] = useState(false)

  function showHint(text: string) {
    setHint(text)
    window.clearTimeout(hintTimer.current)
    hintTimer.current = window.setTimeout(() => setHint(""), 5000)
  }

  // Picked or dropped: each one is checked, then goes in the outbox, in order
  async function takeFiles(files: File[]) {
    for (const file of files) {
      const ready = await prepareFile(file)
      if (typeof ready === "string") showHint(ready)
      else onSendFile(ready)
    }
  }

  const hasFiles = (e: DragEvent) => e.dataTransfer.types.includes("Files")

  // The actions menu, and the message I'm fixing (D39)
  const [menu, setMenu] = useState<OpenMenu | null>(null)
  const [editing, setEditing] = useState<Message | null>(null)
  // The time, so "Edit" goes away once it would be refused
  const [now, setNow] = useState(() => Date.now())
  useEffect(() => {
    const timer = window.setInterval(() => setNow(Date.now()), CLOCK_EVERY_MS)
    return () => clearInterval(timer)
  }, [])

  const age = (message: Message) => now - Date.parse(message.createdAt)
  const canEdit = (message: Message) =>
    message.senderId === myId && message.kind === "text" && age(message) < EDIT_FOR_MS
  const canDelete = (message: Message) => message.senderId === myId && age(message) < DELETE_FOR_MS

  // One change to a saved message. The reply is the message as it is now, so
  // it shows at once, even if the live push is lost (D24). The push still comes,
  // with the change's number.
  async function change(message: Message, path: string, method: string, body?: unknown) {
    try {
      const changed = await api<ServerMessage>(`/chats/${chat.id}/messages/${message.seq}${path}`, { method, body })
      applyChange(changed)
      keep([changed]) // the push does this too, unless Redis is down (D24)
    } catch (error) {
      showHint(groupError(error))
    }
  }

  // Tap the one I already picked to take it back; any other replaces it (D39)
  function toggleReaction(message: Message, emoji: string) {
    if (message.reactions[emoji]?.includes(myId)) change(message, "/reaction", "DELETE")
    else change(message, "/reaction", "PUT", { emoji })
  }

  const myReaction = (message: Message) =>
    REACTIONS.find((emoji) => message.reactions[emoji]?.includes(myId)) ?? null

  // What this message offers. Nothing until it's saved, once deleted, or after I've left.
  function actionsFor(message: Message): BubbleActions | null {
    if (chat.left || message.seq === null || message.deleted) return null
    return {
      canEdit: canEdit(message),
      canDelete: canDelete(message),
      onMenu: (anchor, mode) => setMenu({ message, anchor, mode }),
      onEdit: () => setEditing(message),
      onToggle: (emoji) => toggleReaction(message, emoji),
    }
  }

  // The message as it is now: the one in the menu may have changed since it opened
  const menuMessage = menu && (messages.find((m) => m.clientMsgId === menu.message.clientMsgId) ?? menu.message)

  const group = chat.kind === "group"
  const firstKey = messages[0]?.clientMsgId
  const lastKey = messages.at(-1)?.clientMsgId
  const lastIsMine = messages.at(-1)?.senderId === myId

  // Older messages were added on top: put the same message back under your eyes, no jump
  useLayoutEffect(() => {
    const list = listRef.current
    if (list && fromBottom.current !== null) {
      list.scrollTop = list.scrollHeight - fromBottom.current
      fromBottom.current = null
    }
  }, [firstKey])

  // A new message at the bottom. Show it on first load, when I sent it, or when
  // I was already at the bottom. Scrolled up reading older ones? Their new
  // message doesn't pull me down (D8).
  useLayoutEffect(() => {
    const list = listRef.current
    if (list && (lastIsMine || atBottom.current)) list.scrollTop = list.scrollHeight
  }, [lastKey, lastIsMine])

  // Below 1280px the chat can load while hidden (behind the chat list on a
  // phone, or the side panel), and a hidden list can't scroll. So when it
  // comes into view (it has a height again), show the newest.
  useLayoutEffect(() => {
    const list = listRef.current
    if (list && list.clientHeight > 0) list.scrollTop = list.scrollHeight
  }, [view])

  // The list got shorter or taller: the phone keyboard opened or closed, or
  // "is typing..." came or went. If you were at the bottom, stay there, so the
  // newest message never hides behind the message box.
  useEffect(() => {
    const list = listRef.current
    if (!list) return
    const observer = new ResizeObserver(() => {
      if (atBottom.current) list.scrollTop = list.scrollHeight
    })
    observer.observe(list)
    return () => observer.disconnect()
  }, [])

  // Puts the message in the middle of the list and flashes it. False if it isn't on screen.
  function goTo(seq: number) {
    const list = listRef.current
    const row = list?.querySelector(`[data-seq="${seq}"]`)
    if (!list || !row) return false
    atBottom.current = false // or a resize would pull the list back down
    // By hand, because scrollIntoView can also move the locked page on an iPhone
    const [rowBox, listBox] = [row.getBoundingClientRect(), list.getBoundingClientRect()]
    list.scrollTop += rowBox.top - listBox.top - (list.clientHeight - rowBox.height) / 2
    row.querySelector("[data-bubble]")?.animate(
      [{ boxShadow: "0 0 0 3px var(--primary)" }, { boxShadow: "0 0 0 3px transparent" }],
      { duration: 2000, easing: "ease-in" },
    )
    return true
  }

  // A result was tapped. If the message is further up, page back to it first (D40).
  const runJump = useEffectEvent((seq: number) => {
    onJumped()
    if (goTo(seq)) return
    goingTo.current = seq
    loadBackTo(seq).then((found) => {
      if (found) return
      goingTo.current = null
      showHint("That message isn't in this chat any more.")
    })
  })
  useEffect(() => {
    if (jump !== null && !loading) runJump(jump)
  }, [jump, loading])

  // Older messages arrived: is the one I'm going to among them?
  useLayoutEffect(() => {
    if (goingTo.current !== null && goTo(goingTo.current)) goingTo.current = null
  }, [firstKey])

  // "Read" (D20): this chat is showing, the window is in front, and the newest
  // message is on screen. Then tell the server the highest number with no hole
  // below it (D21), and clear the unread count.
  function reportIfRead() {
    const list = listRef.current
    // No height: the chat can be open but hidden (behind the chat list on a phone, or the side panel)
    if (!list || list.clientHeight === 0 || gapFreeSeq === 0 || !windowInFront()) return
    if (hiddenBelow(list) > NEAR_BOTTOM_PX) return
    reportRead(chat.id, gapFreeSeq)
    onRead()
  }
  const checkRead = useEffectEvent(reportIfRead)

  // The messages load, new ones arrive (live or by catch-up) while you watch, or the chat comes back into view.
  // A layout effect, so the unread count clears before the screen is drawn: no flash of a "1".
  useLayoutEffect(() => {
    checkRead()
  }, [gapFreeSeq, view])

  // You come back to the window or tab: what's on screen now counts as read
  useEffect(() => {
    const check = () => checkRead()
    window.addEventListener("focus", check)
    document.addEventListener("visibilitychange", check)
    return () => {
      window.removeEventListener("focus", check)
      document.removeEventListener("visibilitychange", check)
    }
  }, [])

  // Scrolling down to the newest message reads it. Near the top: load the 30 above.
  function handleScroll() {
    const list = listRef.current
    if (!list) return
    setMenu(null) // it's pinned to where the message was
    atBottom.current = hiddenBelow(list) <= NEAR_BOTTOM_PX
    reportIfRead()
    if (!hasMore || list.scrollTop > 80) return
    fromBottom.current = list.scrollHeight - list.scrollTop
    loadOlder()
  }

  // My #N: teal ✓✓ once they've read up to N, grey ✓✓ once it's on their device (D20)
  function receiptFor(seq: number | null) {
    if (seq === null) return null
    if (seq <= theirRead) return "read"
    if (seq <= theirDelivered) return "delivered"
    return null
  }

  return (
    <section
      // Always stopped, or a file dropped here would open in the tab and leave Parley.
      onDragEnter={(e) => {
        if (!hasFiles(e) || chat.left) return
        dragDepth.current += 1
        setDragging(true)
      }}
      onDragLeave={(e) => {
        if (!hasFiles(e) || chat.left) return
        dragDepth.current -= 1
        if (dragDepth.current === 0) setDragging(false)
      }}
      onDragOver={(e) => {
        e.preventDefault()
        if (chat.left) e.dataTransfer.dropEffect = "none" // the "not allowed" cursor
      }}
      onDrop={(e) => {
        e.preventDefault()
        dragDepth.current = 0
        setDragging(false)
        if (!chat.left) takeFiles([...e.dataTransfer.files])
      }}
      className={cn(
        // Never squeezed below 360px from 768px up. From 1280px the gap on its right comes from the side panel.
        "relative min-h-0 min-w-0 flex-1 flex-col bg-conversation md:my-4 md:mr-4 md:min-w-90 md:rounded-panel xl:mr-0",
        // Phone: only when it's the chat's turn. 768-1279px: unless the side panel took its place.
        view === "chat" ? "flex" : "hidden",
        view === "panel" ? "md:hidden xl:flex" : "md:flex",
      )}
    >
      <header className="flex h-16 shrink-0 items-center gap-3 border-b px-4 md:px-6">
        <button
          type="button"
          onClick={onBack}
          aria-label="Back to chats"
          className="flex size-10 items-center justify-center rounded-lg bg-card text-muted-foreground md:hidden"
        >
          <ArrowLeft className="size-4" />
        </button>
        {/* Below 1280px, tapping the name shows the side panel in the chat's place (D8) */}
        <button
          type="button"
          onClick={onOpenPanel}
          className="flex min-w-0 cursor-pointer items-center gap-3 text-left xl:cursor-default"
        >
          {/* A group's avatar is its name's initials (D37) */}
          <Avatar name={chat.name} tint={tintFor(chat.id)} status={chat.online ? "online" : undefined} />
          <span className="min-w-0">
            <span className="block truncate text-header leading-tight">{chat.name}</span>
            {/* Direct chats: online or last seen (D22). Groups: who's in it, not who's online (D37) */}
            <span className="block truncate text-label text-muted-foreground">
              {group
                ? chat.left
                  ? "You're no longer a member"
                  : memberNames(members, myId) || "\u00a0"
                : chat.online
                  ? "online"
                  : lastSeenText(chat.last_seen)}
            </span>
          </span>
        </button>
        <button
          type="button"
          onClick={() => setSearchOpen(true)}
          aria-label="Search in this chat"
          className="ml-auto flex size-10 shrink-0 items-center justify-center rounded-lg text-rail-icon hover:text-muted-foreground"
        >
          <Search className="size-5" />
        </button>
      </header>

      {/* overflow-anchor none: the browser mustn't move the scroll on its own; handleScroll and the effects do it.
          overscroll-contain: the iPhone's bounce at the top or bottom stays in the list and doesn't drag the page. */}
      <div
        ref={listRef}
        onScroll={handleScroll}
        className="flex min-h-0 flex-1 flex-col gap-5 overflow-y-auto overscroll-contain p-4 [overflow-anchor:none] scrollbar-thin md:p-6"
      >
        {loading && <p className="m-auto text-sm text-muted-foreground">Loading messages...</p>}
        {failed && <p className="m-auto text-sm text-muted-foreground">Can't reach Parley. Reload to try again.</p>}
        {!loading && !failed && messages.length === 0 && (
          <p className="m-auto text-sm text-muted-foreground">No messages yet. Say hi!</p>
        )}
        {messages.map((message) =>
          message.kind === "system" ? (
            <SystemNote key={message.clientMsgId} message={message} myId={myId} />
          ) : (
            <MessageBubble
              key={message.clientMsgId}
              message={message}
              // A direct chat: anyone who isn't me is the other person. A group: whoever sent it,
              // in a color that stays theirs (D37)
              senderName={group ? message.senderName : chat.name}
              senderTint={tintFor(group ? message.senderId : chat.id)}
              mine={message.senderId === myId}
              group={group}
              receipt={receiptFor(message.seq)}
              onRetry={() => onRetry(message)}
              chatId={chat.id}
              onCancel={() => onCancel(message)}
              myId={myId}
              actions={actionsFor(message)}
            />
          ),
        )}
      </div>

      {menu && menuMessage && (
        <MessageMenu
          menu={menu}
          mine={menuMessage.senderId === myId}
          myReaction={myReaction(menuMessage)}
          canEdit={canEdit(menuMessage)}
          canDelete={canDelete(menuMessage)}
          onReact={(emoji) => {
            setMenu(null)
            toggleReaction(menuMessage, emoji)
          }}
          onEdit={() => {
            setMenu(null)
            setEditing(menuMessage)
          }}
          onCopy={() => {
            setMenu(null)
            navigator.clipboard.writeText(menuMessage.body).catch(() => showHint("Couldn't copy that."))
          }}
          onDelete={() => {
            setMenu(null)
            change(menuMessage, "", "DELETE")
          }}
          onClose={() => setMenu(null)}
        />
      )}

      {/* The other person is typing (D20). The three dots bounce one after another. */}
      {typing && (
        <div className="flex shrink-0 items-center gap-3 px-4 pb-3 md:px-6">
          <div className="flex size-9 items-center justify-center gap-1 rounded-full bg-card">
            <span className="size-1 animate-typing rounded-full bg-muted-foreground" />
            <span className="size-1 animate-typing rounded-full bg-muted-foreground [animation-delay:150ms]" />
            <span className="size-1 animate-typing rounded-full bg-muted-foreground [animation-delay:300ms]" />
          </div>
          <p className="text-label">{group ? typing.name : chat.name} is typing...</p>
        </div>
      )}

      {/* Clear of the iPhone's home bar when it overlaps the page; 16px otherwise (the browser's own tab already keeps clear) */}
      <div className="shrink-0 px-4 pb-[max(1rem,env(safe-area-inset-bottom))]">
        {chat.left ? (
          // Left or removed: read-only, with a note instead of the message box (D37)
          <p className="flex min-h-16 items-center justify-center rounded-panel bg-card/60 px-4 text-center text-sm text-muted-foreground">
            You can't send messages to this group because you're no longer a member.
          </p>
        ) : (
          <>
            {hint && (
              <p role="status" className="mb-2 truncate text-center text-label text-destructive">
                {hint}
              </p>
            )}
            {/* Hidden, not removed, so whatever I was writing is still there afterwards */}
            <div className={editing ? "hidden" : undefined}>
              <MessageBox
                onSend={onSend}
                onTyping={() => sendTyping(chat.id)}
                onFiles={takeFiles}
                onVoice={onSendFile}
                onHint={showHint}
              />
            </div>
            {editing && (
              <EditBox
                key={editing.clientMsgId}
                original={editing.body}
                onCancel={() => setEditing(null)}
                onSave={(body) => {
                  setEditing(null)
                  change(editing, "", "PATCH", { body })
                }}
              />
            )}
          </>
        )}
      </div>

      {searchOpen && (
        <ChatSearch
          chat={chat}
          myId={myId}
          query={searchQuery}
          onQuery={setSearchQuery}
          history={history}
          onOpen={(hit) => {
            setSearchOpen(false)
            onOpenHit(hit)
          }}
          onClose={() => {
            setSearchOpen(false)
            setSearchQuery("")
          }}
        />
      )}

      {/* Dropping files: the screen from the reference design (D8) */}
      {dragging && (
        <div className="pointer-events-none absolute inset-0 flex items-center justify-center bg-conversation/90 p-4 backdrop-blur-sm md:rounded-panel">
          <div className="flex size-full flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed border-primary/50 p-6 text-center">
            <span className="mb-4 flex size-24 items-center justify-center rounded-full bg-primary text-primary-foreground shadow-lg shadow-primary/30 ring-[16px] ring-primary/15">
              <FolderUp className="size-9" />
            </span>
            <p className="text-2xl font-medium">Upload your file</p>
            <p className="text-muted-foreground">
              to <span className="text-primary">{chat.name}</span>
              {group ? " group" : ""}
            </p>
          </div>
        </div>
      )}
    </section>
  )
}
