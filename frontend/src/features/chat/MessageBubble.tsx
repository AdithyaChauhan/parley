import { Avatar } from "@/components/Avatar"
import { Ticks } from "@/components/Ticks"
import type { Message, Person } from "@/data/fake"

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

type MessageBubbleProps = {
  message: Message
  sender: Person
  mine: boolean
}

// One message: a "Name, time" label above a bubble.
// Their bubble: sharp bottom-left corner, next to the avatar. My bubble: sharp bottom-right corner.
export function MessageBubble({ message, sender, mine }: MessageBubbleProps) {
  if (mine) {
    return (
      <div className="flex flex-col items-end gap-2">
        <p className="flex items-center gap-1 text-label">
          You, {message.time}
          {message.tick && <Ticks status={message.tick} />}
        </p>
        <div className="max-w-[80%] rounded-panel rounded-br-none bg-bubble-mine px-4 py-3 wrap-break-word">
          {withMentions(message.text)}
        </div>
      </div>
    )
  }

  return (
    <div className="flex items-end gap-3">
      <Avatar name={sender.name} tint={sender.tint} size="sm" />
      <div className="flex max-w-[80%] min-w-0 flex-col items-start gap-2">
        <p className="text-label">
          {sender.name}, {message.time}
        </p>
        <div className="rounded-panel rounded-bl-none bg-bubble-theirs px-4 py-3 shadow-sm shadow-foreground/5 wrap-break-word">
          {withMentions(message.text)}
        </div>
      </div>
    </div>
  )
}
