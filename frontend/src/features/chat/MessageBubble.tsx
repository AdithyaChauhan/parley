import { useRef, type PointerEvent, type ReactNode } from "react"
import { Ban, Pencil, SmilePlus, Trash2 } from "lucide-react"
import { Avatar } from "@/components/Avatar"
import { Ticks } from "@/components/Ticks"
import { cn } from "@/lib/utils"
import { FileContent } from "./FileContent"
import { noteText } from "./groupNotes"
import type { MenuMode } from "./MessageMenu"
import { clockTime } from "./time"
import { REACTIONS, type Message, type Reactions, type SystemData, type Tint } from "./types"

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

// What can be done to this message (D39). Null: nothing (not saved yet, deleted, or I left).
export type BubbleActions = {
  canEdit: boolean
  canDelete: boolean
  onMenu: (anchor: DOMRect, mode: MenuMode) => void
  onEdit: () => void
  onToggle: (emoji: string) => void // tapping a count under the bubble
}

// A finger held still this long opens the menu (phones and tablets, D39)
const LONG_PRESS_MS = 450
const MOVE_TOLERANCE_PX = 10

function useLongPress(onLongPress: (element: HTMLElement) => void) {
  const timer = useRef<number | undefined>(undefined)
  const start = useRef({ x: 0, y: 0 })
  const stop = () => window.clearTimeout(timer.current)
  return {
    onPointerDown(e: PointerEvent<HTMLElement>) {
      if (e.pointerType === "mouse") return // hovering does it on desktop
      start.current = { x: e.clientX, y: e.clientY }
      const element = e.currentTarget
      timer.current = window.setTimeout(() => onLongPress(element), LONG_PRESS_MS)
    },
    onPointerMove(e: PointerEvent<HTMLElement>) {
      if (Math.hypot(e.clientX - start.current.x, e.clientY - start.current.y) > MOVE_TOLERANCE_PX) stop()
    },
    onPointerUp: stop,
    onPointerCancel: stop,
  }
}

// The small buttons beside a bubble, only while the mouse is over it (D39).
// No gap between them and the bubble, or the mouse would lose them on the way.
function HoverButtons({ actions, side }: { actions: BubbleActions; side: "left" | "right" }) {
  const button = "flex size-7 items-center justify-center rounded-md text-muted-foreground hover:bg-row-selected"
  const open = (mode: MenuMode) => (e: { currentTarget: HTMLElement }) => {
    const bubble = e.currentTarget.closest("[data-bubble]")
    actions.onMenu((bubble ?? e.currentTarget).getBoundingClientRect(), mode)
  }
  return (
    <div
      className={cn(
        "absolute top-1/2 z-10 hidden -translate-y-1/2 group-hover/bubble:flex",
        side === "left" ? "right-full pr-1" : "left-full pl-1",
      )}
    >
      <div className="flex rounded-lg bg-card shadow-sm ring-1 shadow-foreground/5 ring-border">
        <button type="button" aria-label="React" onClick={open("emojis")} className={button}>
          <SmilePlus className="size-4" />
        </button>
        {actions.canEdit && (
          <button type="button" aria-label="Edit message" onClick={actions.onEdit} className={button}>
            <Pencil className="size-4" />
          </button>
        )}
        {actions.canDelete && (
          <button type="button" aria-label="Delete for everyone" onClick={open("confirm")} className={button}>
            <Trash2 className="size-4" />
          </button>
        )}
      </div>
    </div>
  )
}

// The counts under a bubble, in the same order everywhere (D39). Mine has a teal ring.
function ReactionCounts({
  reactions,
  myId,
  onToggle,
}: {
  reactions: Reactions
  myId: string
  onToggle?: (emoji: string) => void
}) {
  const shown = REACTIONS.filter((emoji) => reactions[emoji]?.length)
  if (shown.length === 0) return null
  return (
    <div className="flex flex-wrap gap-1">
      {shown.map((emoji) => (
        <button
          key={emoji}
          type="button"
          disabled={!onToggle}
          aria-label={`${emoji} ${reactions[emoji].length}`}
          aria-pressed={reactions[emoji].includes(myId)}
          onClick={() => onToggle?.(emoji)}
          className={cn(
            "flex h-6 items-center gap-1 rounded-full bg-card px-2 text-xs shadow-sm shadow-foreground/5",
            reactions[emoji].includes(myId) && "ring-1 ring-primary",
          )}
        >
          <span>{emoji}</span>
          <span className="tabular-nums">{reactions[emoji].length}</span>
        </button>
      ))}
    </div>
  )
}

function Deleted() {
  return (
    <span className="flex items-center gap-1.5 text-muted-foreground italic">
      <Ban className="size-3.5 shrink-0" />
      This message was deleted
    </span>
  )
}

// The bubble's wrapper: the hover buttons and the long press both live here.
// Long press: no selection or iPhone callout on touch screens, or they'd fight the menu.
function Pressable({
  actions,
  side,
  className,
  children,
}: {
  actions: BubbleActions | null
  side: "left" | "right"
  className: string
  children: ReactNode
}) {
  const press = useLongPress((element) => {
    actions?.onMenu((element.querySelector("[data-bubble]") ?? element).getBoundingClientRect(), "all")
  })
  return (
    <div
      {...(actions ? press : {})}
      className={cn(
        "group/bubble relative",
        className,
        actions && "pointer-coarse:select-none pointer-coarse:[-webkit-touch-callout:none]",
      )}
    >
      {children}
      {actions && <HoverButtons actions={actions} side={side} />}
    </div>
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
  myId: string
  actions: BubbleActions | null
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
  myId,
  actions,
}: MessageBubbleProps) {
  const time = clockTime(message.createdAt)
  const isFile = message.kind === "file" && !message.deleted
  const content = message.deleted ? (
    <Deleted />
  ) : isFile ? (
    <FileContent chatId={chatId} message={message} onCancel={onCancel} />
  ) : (
    withMentions(message.body)
  )
  const edited = message.edited && !message.deleted && <span className="text-muted-foreground">· edited</span>
  const counts = <ReactionCounts reactions={message.reactions} myId={myId} onToggle={actions?.onToggle} />

  if (mine) {
    const unsaved = message.status === "sending" || message.status === "waiting"
    return (
      <div className="flex flex-col items-end gap-2">
        <p className="flex items-center gap-1 text-label">
          You, {time} {edited}
          {/* Waiting also gets the clock: it's still on its way */}
          {message.status !== "failed" && <Ticks status={receipt ?? (unsaved ? "sending" : "sent")} />}
        </p>
        <Pressable actions={actions} side="left" className="max-w-[75%]">
          <div
            data-bubble
            className={cn(
              "rounded-panel rounded-br-none bg-bubble-mine wrap-break-word",
              isFile ? "p-2" : "px-4 py-3",
              // A file shows its own progress, so it isn't faded too
              unsaved && !isFile && "opacity-60",
            )}
          >
            {content}
          </div>
        </Pressable>
        {counts}
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
      {/* Beside the bubble, not beside the counts under it */}
      <div className={cn("shrink-0", REACTIONS.some((emoji) => message.reactions[emoji]?.length) && "mb-8")}>
        <Avatar name={senderName} tint={senderTint} size="sm" />
      </div>
      <div className="flex max-w-[75%] min-w-0 flex-col items-start gap-2">
        <p className="flex items-center gap-1 text-label">
          <span>
            <span className={cn(group && cn("font-medium", nameColors[senderTint]))}>{senderName}</span>, {time}
          </span>
          {edited}
        </p>
        <Pressable actions={actions} side="right" className="max-w-full">
          <div
            data-bubble
            className={cn(
              "rounded-panel rounded-bl-none bg-bubble-theirs shadow-sm shadow-foreground/5 wrap-break-word",
              isFile ? "p-2" : "px-4 py-3",
            )}
          >
            {content}
          </div>
        </Pressable>
        {counts}
      </div>
    </div>
  )
}
