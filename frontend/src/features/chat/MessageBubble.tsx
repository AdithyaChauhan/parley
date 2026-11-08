import { Avatar } from "@/components/Avatar"
import { Ticks } from "@/components/Ticks"
import { cn } from "@/lib/utils"
import { FileContent } from "./FileContent"
import { noteText } from "./groupNotes"
import { clockTime } from "./time"
import type { Message, SystemData, Tint } from "./types"

// Shows "@Name" in teal (look.md: @mentions use the teal accent)
function withMentions(text: string) {
  return text.split(/(@\w+)/).map((part, i) =>
    part.startsWith("@") ? (
      <span key={i} className="text-primary">
        {part}
      </span>
    ) : (
      part
    ),
  )
}

// A sender's name in a group, in the darker shade of their avatar's tint, so
// each person keeps one color (D37)
const nameColors: Record<Tint, string> = {
  teal: "text-file-teal-icon",
  purple: "text-file-purple-icon",
  yellow: "text-file-yellow-icon",
  red: "text-file-red-icon",
}

// A group note: "Ana added Ben", small and centered, with no bubble (D37)
export function SystemNote({ message, myId }: { message: Message; myId: string }) {
  if (!message.data) return null
  return (
    <p className="mx-auto max-w-[85%] rounded-lg bg-card/70 px-3 py-1.5 text-center text-label text-muted-foreground">
      {noteText(message.data as SystemData, myId)}
    </p>
  )
}

type MessageBubbleProps = {
  message: Message
  senderName: string
  senderTint: Tint
  mine: boolean
  group: boolean // in a group, their name takes their own color
  // How far my message got on the other side: on their device (grey ✓✓), read (teal ✓✓), or not yet
  receipt: "delivered" | "read" | null
  onRetry: () => void
  chatId: string
  onCancel: () => void // stops a file on its way
}

// One message: a "Name, time" label above a bubble.
// Their bubble: sharp bottom-left corner, next to the avatar. My bubble: sharp bottom-right corner.
export function MessageBubble({
  message,
  senderName,
  senderTint,
  mine,
  group,
  receipt,
  onRetry,
  chatId,
  onCancel,
}: MessageBubbleProps) {
  const time = clockTime(message.createdAt)
  const isFile = message.kind === "file"
  const content = isFile ? (
    <FileContent chatId={chatId} message={message} onCancel={onCancel} />
  ) : (
    withMentions(message.body)
  )

  if (mine) {
    const unsaved = message.status === "sending" || message.status === "waiting"
    return (
      <div className="flex flex-col items-end gap-2">
        <p className="flex items-center gap-1 text-label">
          You, {time}
          {/* Waiting also gets the clock: it's still on its way */}
          {message.status !== "failed" && <Ticks status={receipt ?? (unsaved ? "sending" : "sent")} />}
        </p>
        <div
          className={cn(
            "max-w-[75%] rounded-panel rounded-br-none bg-bubble-mine wrap-break-word",
            isFile ? "p-2" : "px-4 py-3",
            // A file shows its own progress, so it isn't faded too
            unsaved && !isFile && "opacity-60",
          )}
        >
          {content}
        </div>
        {/* Offline: it goes out by itself when the line is back (D21) */}
        {message.status === "waiting" && <p className="text-label">Waiting for connection</p>}
        {message.status === "failed" && (
          <button type="button" onClick={onRetry} className="text-label text-destructive hover:underline">
            Not sent, tap to retry
          </button>
        )}
      </div>
    )
  }

  return (
    <div className="flex items-end gap-3">
      <Avatar name={senderName} tint={senderTint} size="sm" />
      <div className="flex max-w-[75%] min-w-0 flex-col items-start gap-2">
        <p className="text-label">
          <span className={cn(group && cn("font-medium", nameColors[senderTint]))}>{senderName}</span>, {time}
        </p>
        <div
          className={cn(
            "max-w-full rounded-panel rounded-bl-none bg-bubble-theirs shadow-sm shadow-foreground/5 wrap-break-word",
            isFile ? "p-2" : "px-4 py-3",
          )}
        >
          {content}
        </div>
      </div>
    </div>
  )
}
