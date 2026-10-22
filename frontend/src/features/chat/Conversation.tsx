import { useEffect, useEffectEvent, useLayoutEffect, useRef, useState, type DragEvent } from "react"
import { ArrowLeft } from "lucide-react"
import { reportRead, sendTyping, windowInFront } from "@/lib/live"
import { cn } from "@/lib/utils"
import { MessageBox } from "./MessageBox"
import { MessageBubble } from "./MessageBubble"
import { tintFor, type ChatSummary, type Message, type ServerMessage } from "./types"
import { UploadView } from "./UploadView"
import { useMessages, type UpdateUnsent } from "./useMessages"

// Scrolled up less than this counts as "at the bottom": the newest message is on screen
const NEAR_BOTTOM_PX = 80

// How much of the list is below what you can see, in pixels
function hiddenBelow(list: HTMLElement) {
  return list.scrollHeight - list.scrollTop - list.clientHeight
}

type ConversationProps = {
  chat: ChatSummary
  myId: string
  unsent: Message[] // my messages in this chat that aren't saved yet
  updateUnsent: UpdateUnsent
  onSent: (message: ServerMessage) => void
  typing: boolean // the other person is typing here
  onRead: () => void // I've seen everything here: the chat list sets unread to 0
  onBack: () => void
  onOpenPanel: () => void
  phoneVisible: boolean
}

// The middle panel: title and tabs, the messages, and the message box
export function Conversation({
  chat,
  myId,
  unsent,
  updateUnsent,
  onSent,
  typing,
  onRead,
  onBack,
  onOpenPanel,
  phoneVisible,
}: ConversationProps) {
  const { messages, newestSeq, theirDelivered, theirRead, hasMore, loading, failed, loadOlder, send, retry } =
    useMessages(chat.id, myId, unsent, updateUnsent, onSent)
  const [dragging, setDragging] = useState(false)
  const listRef = useRef<HTMLDivElement>(null)
  // How far from the bottom you were when older messages were asked for
  const fromBottom = useRef<number | null>(null)
  // You're at the newest message, so the list keeps the bottom in view
  const atBottom = useRef(true)

  const firstKey = messages[0]?.clientMsgId
  const lastKey = messages.at(-1)?.clientMsgId

  // Older messages were added on top: put the same message back under your eyes, no jump
  useLayoutEffect(() => {
    const list = listRef.current
    if (list && fromBottom.current !== null) {
      list.scrollTop = list.scrollHeight - fromBottom.current
      fromBottom.current = null
    }
  }, [firstKey])

  // First load, or a new message at the bottom: show the newest
  useLayoutEffect(() => {
    const list = listRef.current
    if (list) list.scrollTop = list.scrollHeight
  }, [lastKey])

  // On a phone the chat loads while hidden behind the chat list, and a hidden
  // list can't scroll. So when it comes into view, show the newest.
  useLayoutEffect(() => {
    const list = listRef.current
    if (list && phoneVisible) list.scrollTop = list.scrollHeight
  }, [phoneVisible])

  // "is typing..." came or went, so the list got shorter or taller: if you were at the bottom, stay there
  useLayoutEffect(() => {
    const list = listRef.current
    if (list && atBottom.current) list.scrollTop = list.scrollHeight
  }, [typing])

  // "Read" (D20): this chat is showing, the window is in front, and the newest
  // message is on screen. Then tell the server the highest number, and clear the unread count.
  function reportIfRead() {
    const list = listRef.current
    // No height: on a phone the chat can be open but hidden behind the chat list
    if (!list || list.clientHeight === 0 || newestSeq === 0 || !windowInFront()) return
    if (hiddenBelow(list) > NEAR_BOTTOM_PX) return
    reportRead(chat.id, newestSeq)
    onRead()
  }
  const checkRead = useEffectEvent(reportIfRead)

  // The messages load, a new one arrives while you watch, or the chat comes into view on a phone.
  // A layout effect, so the unread count clears before the screen is drawn: no flash of a "1".
  useLayoutEffect(() => {
    checkRead()
  }, [newestSeq, phoneVisible])

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

  function handleDragEnter(e: DragEvent) {
    if (e.dataTransfer.types.includes("Files")) setDragging(true)
  }

  // Only hide the upload view when the file leaves the whole panel, not when it moves over a child
  function handleDragLeave(e: DragEvent) {
    if (!e.currentTarget.contains(e.relatedTarget as Node | null)) setDragging(false)
  }

  function handleDrop(e: DragEvent) {
    e.preventDefault() // stop the browser opening the file
    setDragging(false)
  }

  return (
    <section
      onDragEnter={handleDragEnter}
      onDragOver={(e) => e.preventDefault()} // needed so the browser allows a drop here
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      className={cn(
        "relative min-h-0 min-w-0 flex-1 flex-col bg-conversation md:my-4 md:rounded-panel",
        phoneVisible ? "flex" : "hidden md:flex",
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
        <button type="button" onClick={onOpenPanel} className="min-w-0 truncate text-left text-header md:cursor-default">
          {chat.name}
        </button>
        <div className="ml-auto hidden gap-1 md:flex">
          <button type="button" className="h-10 rounded-lg bg-tab-active px-6 text-primary">
            Messages
          </button>
          <button type="button" className="h-10 rounded-lg px-6 text-muted-foreground">
            Participants
          </button>
        </div>
      </header>

      {/* overflow-anchor none: the browser mustn't move the scroll on its own; handleScroll and the effects do it */}
      <div
        ref={listRef}
        onScroll={handleScroll}
        className="flex min-h-0 flex-1 flex-col gap-5 overflow-y-auto p-4 [overflow-anchor:none] scrollbar-thin md:p-6"
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
            onRetry={() => retry(message)}
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

      <div className="shrink-0 px-4 pb-4">
        <MessageBox onSend={send} onTyping={() => sendTyping(chat.id)} />
      </div>

      {dragging && <UploadView chatName={chat.name} isGroup={chat.kind !== "direct"} />}
    </section>
  )
}
