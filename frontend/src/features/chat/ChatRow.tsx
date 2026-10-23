import { Avatar } from "@/components/Avatar"
import { cn } from "@/lib/utils"
import { listTime } from "./time"
import { tintFor, type ChatSummary } from "./types"

type ChatRowProps = {
  chat: ChatSummary
  selected: boolean
  typing: boolean // the other person is typing: "typing..." replaces the preview
  onSelect: () => void
}

// One row in the chat list: avatar, name, time, last message and unread count
export function ChatRow({ chat, selected, typing, onSelect }: ChatRowProps) {
  const last = chat.last_message

  return (
    <button
      type="button"
      onClick={onSelect}
      className={cn(
        "flex w-full items-center gap-3 rounded-lg px-4 py-4 text-left",
        selected ? "bg-row-selected" : "hover:bg-row-selected/60",
      )}
    >
      {/* A green dot only while they're online, like WhatsApp (D22) */}
      <Avatar name={chat.name} tint={tintFor(chat.id)} status={chat.online ? "online" : undefined} />
      <div className="min-w-0 flex-1">
        <div className="flex items-baseline justify-between gap-2">
          <span className="truncate text-name leading-tight">{chat.name}</span>
          <span className="shrink-0 text-label text-muted-foreground">{last && listTime(last.created_at)}</span>
        </div>
        <div className="mt-1 flex items-center justify-between gap-2">
          <span className="truncate text-sm text-muted-foreground">
            {typing ? "typing..." : last ? last.preview : "No messages yet"}
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
