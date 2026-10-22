import { useLayoutEffect, useRef, useState, type DragEvent } from "react"
import { ArrowLeft } from "lucide-react"
import { cn } from "@/lib/utils"
import { MessageBox } from "./MessageBox"
import { MessageBubble } from "./MessageBubble"
import { tintFor, type ChatSummary, type Message, type ServerMessage } from "./types"
import { UploadView } from "./UploadView"
import { useMessages, type UpdateUnsent } from "./useMessages"

type ConversationProps = {
  chat: ChatSummary
  myId: string
  unsent: Message[] // my messages in this chat that aren't saved yet
  updateUnsent: UpdateUnsent
  onSent: (message: ServerMessage) => void
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
  onBack,
  onOpenPanel,
  phoneVisible,
}: ConversationProps) {
  const { messages, theirDelivered, hasMore, loading, failed, loadOlder, send, retry } = useMessages(
    chat.id,
    myId,
    unsent,
    updateUnsent,
    onSent,
  )
  const [dragging, setDragging] = useState(false)
  const listRef = useRef<HTMLDivElement>(null)
  // How far from the bottom you were when older messages were asked for
  const fromBottom = useRef<number | null>(null)

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

  // Near the top: load the 30 above
  function handleScroll() {
    const list = listRef.current
    if (!list || !hasMore || list.scrollTop > 80) return
    fromBottom.current = list.scrollHeight - list.scrollTop
    loadOlder()
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
            // ✓✓ once the other person's device has everything up to this number (D20)
            delivered={message.seq !== null && message.seq <= theirDelivered}
            onRetry={() => retry(message)}
          />
        ))}
      </div>

      <div className="shrink-0 px-4 pb-4">
        <MessageBox onSend={send} />
      </div>

      {dragging && <UploadView chatName={chat.name} isGroup={chat.kind !== "direct"} />}
    </section>
  )
}
