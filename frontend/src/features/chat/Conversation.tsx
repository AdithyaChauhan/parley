import { useEffect, useRef, useState, type DragEvent } from "react"
import { ArrowLeft } from "lucide-react"
import { people, type Chat } from "@/data/fake"
import { cn } from "@/lib/utils"
import { MessageBox } from "./MessageBox"
import { MessageBubble } from "./MessageBubble"
import { UploadView } from "./UploadView"

type ConversationProps = {
  chat: Chat
  onSend: (text: string) => void
  onBack: () => void
  onOpenPanel: () => void
  phoneVisible: boolean
}

// The middle panel: title and tabs, the messages, "is typing", and the message box
export function Conversation({ chat, onSend, onBack, onOpenPanel, phoneVisible }: ConversationProps) {
  const [dragging, setDragging] = useState(false)
  const endRef = useRef<HTMLDivElement>(null)

  // Jump to the newest message when a chat opens or a message is added
  useEffect(() => {
    endRef.current?.scrollIntoView()
  }, [chat.id, chat.messages.length])

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

  const typingName = chat.typingId ? people[chat.typingId].name.split(" ")[0] : null

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

      <div className="flex min-h-0 flex-1 flex-col gap-5 overflow-y-auto p-4 scrollbar-thin md:p-6">
        {chat.messages.map((message) => (
          <MessageBubble
            key={message.id}
            message={message}
            sender={people[message.senderId]}
            mine={message.senderId === "me"}
          />
        ))}
        <div ref={endRef} />
      </div>

      {typingName && (
        <div className="flex shrink-0 items-center gap-3 px-4 pb-3 md:px-6">
          <div className="flex size-9 items-center justify-center gap-1 rounded-full bg-card">
            <span className="size-1 animate-typing rounded-full bg-muted-foreground" />
            <span className="size-1 animate-typing rounded-full bg-muted-foreground [animation-delay:150ms]" />
            <span className="size-1 animate-typing rounded-full bg-muted-foreground [animation-delay:300ms]" />
          </div>
          <p className="text-label">{typingName} is typing</p>
        </div>
      )}

      <div className="shrink-0 px-4 pb-4">
        <MessageBox onSend={onSend} />
      </div>

      {dragging && <UploadView chatName={chat.name} isGroup={chat.isGroup} />}
    </section>
  )
}
