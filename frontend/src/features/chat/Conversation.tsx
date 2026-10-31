import { useEffect, useEffectEvent, useLayoutEffect, useRef } from "react"
import { ArrowLeft } from "lucide-react"
import { Avatar } from "@/components/Avatar"
import { reportRead, sendTyping, windowInFront } from "@/lib/live"
import { cn } from "@/lib/utils"
import { MessageBox } from "./MessageBox"
import { MessageBubble } from "./MessageBubble"
import { lastSeenText } from "./time"
import { tintFor, type ChatSummary, type Message, type NarrowView } from "./types"
import { useMessages } from "./useMessages"

// Scrolled up less than this counts as "at the bottom": the newest message is on screen
const NEAR_BOTTOM_PX = 80

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
  typing: boolean // the other person is typing here
  onRead: () => void // I've seen everything here: the chat list sets unread to 0
  onBack: () => void
  onOpenPanel: () => void // below 1280px: the side panel takes this conversation's place
  view: NarrowView // below 1280px: what has the shared spot
  listChecks: number // goes up each time the chat list re-checks the server
  lineDown: boolean // the live line dropped or failed: nothing is pushed now
}

// The middle panel: who you're talking to, the messages, and the message box
export function Conversation({
  chat,
  myId,
  unsent,
  onSend,
  onRetry,
  typing,
  onRead,
  onBack,
  onOpenPanel,
  view,
  listChecks,
  lineDown,
}: ConversationProps) {
  const { messages, gapFreeSeq, theirDelivered, theirRead, hasMore, loading, failed, loadOlder } = useMessages(
    chat.id,
    myId,
    unsent,
    { seq: chat.last_message?.seq ?? 0, checks: listChecks, lineDown },
  )
  const listRef = useRef<HTMLDivElement>(null)
  // How far from the bottom you were when older messages were asked for
  const fromBottom = useRef<number | null>(null)
  // You're at the newest message, so the list keeps the bottom in view
  const atBottom = useRef(true)

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
      // No file drops until v2 (D8). Without this, a file dropped here would open in the tab and leave Parley.
      onDragOver={(e) => {
        e.preventDefault()
        e.dataTransfer.dropEffect = "none" // the "not allowed" cursor
      }}
      onDrop={(e) => e.preventDefault()}
      className={cn(
        // Never squeezed below 360px from 768px up. From 1280px the gap on its right comes from the side panel.
        "min-h-0 min-w-0 flex-1 flex-col bg-conversation md:my-4 md:mr-4 md:min-w-90 md:rounded-panel xl:mr-0",
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
          <Avatar name={chat.name} tint={tintFor(chat.id)} status={chat.online ? "online" : undefined} />
          <span className="min-w-0">
            <span className="block truncate text-header leading-tight">{chat.name}</span>
            {/* Online or last seen, for direct chats (D22) */}
            {chat.kind === "direct" && (
              <span className="block truncate text-label text-muted-foreground">
                {chat.online ? "online" : lastSeenText(chat.last_seen)}
              </span>
            )}
          </span>
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
        {messages.map((message) => (
          <MessageBubble
            key={message.clientMsgId}
            message={message}
            senderName={chat.name} // a direct chat: anyone who isn't me is the other person
            senderTint={tintFor(chat.id)}
            mine={message.senderId === myId}
            receipt={receiptFor(message.seq)}
            onRetry={() => onRetry(message)}
          />
        ))}
      </div>

      {/* The other person is typing (D20). The three dots bounce one after another. */}
      {typing && (
        <div className="flex shrink-0 items-center gap-3 px-4 pb-3 md:px-6">
          <div className="flex size-9 items-center justify-center gap-1 rounded-full bg-card">
            <span className="size-1 animate-typing rounded-full bg-muted-foreground" />
            <span className="size-1 animate-typing rounded-full bg-muted-foreground [animation-delay:150ms]" />
            <span className="size-1 animate-typing rounded-full bg-muted-foreground [animation-delay:300ms]" />
          </div>
          <p className="text-label">{chat.name} is typing...</p>
        </div>
      )}

      {/* Clear of the iPhone's home bar when it overlaps the page; 16px otherwise (the browser's own tab already keeps clear) */}
      <div className="shrink-0 px-4 pb-[max(1rem,env(safe-area-inset-bottom))]">
        <MessageBox onSend={onSend} onTyping={() => sendTyping(chat.id)} />
      </div>
    </section>
  )
}
