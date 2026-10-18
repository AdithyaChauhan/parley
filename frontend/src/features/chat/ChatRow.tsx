import { Avatar } from "@/components/Avatar"
import type { Chat } from "@/data/fake"
import { cn } from "@/lib/utils"

type ChatRowProps = {
  chat: Chat
  selected: boolean
  onSelect: () => void
}

// One row in the chat list: avatar, name, time, last message and unread count
export function ChatRow({ chat, selected, onSelect }: ChatRowProps) {
  const last = chat.messages[chat.messages.length - 1]

  return (
    <button
      type="button"
      onClick={onSelect}
      className={cn(
        "flex w-full items-center gap-3 rounded-lg px-4 py-4 text-left",
        selected ? "bg-row-selected" : "hover:bg-row-selected/60",
      )}
    >
      <Avatar name={chat.name} tint={chat.tint} />
      <div className="min-w-0 flex-1">
        <div className="flex items-baseline justify-between gap-2">
          <span className="truncate text-name leading-tight">{chat.name}</span>
          <span className="shrink-0 text-label text-muted-foreground">{chat.day ?? last.time}</span>
        </div>
        <div className="mt-1 flex items-center justify-between gap-2">
          <span className="truncate text-sm text-muted-foreground">
            {chat.typingId ? "typing..." : last.text}
          </span>
          {chat.unread > 0 && (
            <span className="flex h-5 min-w-5 shrink-0 items-center justify-center rounded-full bg-primary px-1.5 text-[11px] font-medium text-primary-foreground">
              {chat.unread}
            </span>
          )}
        </div>
      </div>
    </button>
  )
}
