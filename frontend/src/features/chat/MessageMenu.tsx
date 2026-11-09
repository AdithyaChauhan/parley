import { useEffect, useEffectEvent, useRef, useState } from "react"
import { Copy, Pencil, Trash2 } from "lucide-react"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import { REACTIONS, type Message } from "./types"

// What the menu shows. "all" is the phone's long press. On desktop, the hover
// buttons open just the emojis, or just the "are you sure" (D39).
export type MenuMode = "all" | "emojis" | "confirm"
export type OpenMenu = { message: Message; anchor: DOMRect; mode: MenuMode }

type MessageMenuProps = {
  menu: OpenMenu
  mine: boolean // my bubbles are on the right
  myReaction: string | null
  canEdit: boolean
  canDelete: boolean
  onReact: (emoji: string) => void
  onEdit: () => void
  onCopy: () => void
  onDelete: () => void
  onClose: () => void
}

const WIDTH_PX = 272
const EDGE_PX = 8
// Roughly the tallest this gets: under this much room above, it opens below instead
const TALLEST_PX = 190

// A small box next to the message. Fixed to the window, so the message list
// can't cut it off.
export function MessageMenu({
  menu,
  mine,
  myReaction,
  canEdit,
  canDelete,
  onReact,
  onEdit,
  onCopy,
  onDelete,
  onClose,
}: MessageMenuProps) {
  const [confirming, setConfirming] = useState(menu.mode === "confirm")
  const box = useRef<HTMLDivElement>(null)
  const close = useEffectEvent(onClose)

  // A tap or click anywhere else, or Esc, closes it
  useEffect(() => {
    function closeIfOutside(e: PointerEvent) {
      if (!box.current?.contains(e.target as Node)) close()
    }
    function closeOnEsc(e: KeyboardEvent) {
      if (e.key === "Escape") close()
    }
    document.addEventListener("pointerdown", closeIfOutside)
    document.addEventListener("keydown", closeOnEsc)
    return () => {
      document.removeEventListener("pointerdown", closeIfOutside)
      document.removeEventListener("keydown", closeOnEsc)
    }
  }, [])

  const { anchor } = menu
  // Lined up with the bubble's outer edge, so it stays over the conversation
  const wanted = mine ? anchor.right - WIDTH_PX : anchor.left
  const left = Math.max(EDGE_PX, Math.min(wanted, window.innerWidth - WIDTH_PX - EDGE_PX))
  const above = anchor.top > TALLEST_PX
  const position = above
    ? { bottom: window.innerHeight - anchor.top + EDGE_PX, left, width: WIDTH_PX }
    : { top: anchor.bottom + EDGE_PX, left, width: WIDTH_PX }

  const rowClass = "flex w-full items-center gap-3 rounded-md px-3 py-2 text-left text-sm hover:bg-row-selected"

  return (
    <div
      ref={box}
      style={position}
      className="fixed z-30 rounded-lg bg-card p-1 shadow-lg ring-1 shadow-foreground/10 ring-border"
    >
      {confirming ? (
        <div className="p-2">
          <p className="text-sm font-medium">Delete for everyone?</p>
          <p className="mt-1 text-sm text-muted-foreground">This can't be undone.</p>
          <div className="mt-3 flex justify-end gap-2">
            <Button type="button" variant="ghost" size="sm" onClick={onClose}>
              Cancel
            </Button>
            <Button type="button" variant="destructive" size="sm" onClick={onDelete}>
              Delete
            </Button>
          </div>
        </div>
      ) : (
        <>
          <div className="flex justify-between">
            {REACTIONS.map((emoji) => (
              <button
                key={emoji}
                type="button"
                aria-label={`React with ${emoji}`}
                aria-pressed={emoji === myReaction}
                onClick={() => onReact(emoji)}
                className={cn(
                  "flex size-10 items-center justify-center rounded-lg text-xl hover:bg-row-selected",
                  emoji === myReaction && "bg-accent",
                )}
              >
                {emoji}
              </button>
            ))}
          </div>
          {menu.mode === "all" && (
            <>
              {menu.message.kind === "text" && (
                <button type="button" onClick={onCopy} className={rowClass}>
                  <Copy className="size-4 text-muted-foreground" />
                  Copy
                </button>
              )}
              {canEdit && (
                <button type="button" onClick={onEdit} className={rowClass}>
                  <Pencil className="size-4 text-muted-foreground" />
                  Edit
                </button>
              )}
              {canDelete && (
                <button
                  type="button"
                  onClick={() => setConfirming(true)}
                  className={cn(rowClass, "text-destructive")}
                >
                  <Trash2 className="size-4" />
                  Delete for everyone
                </button>
              )}
            </>
          )}
        </>
      )}
    </div>
  )
}
