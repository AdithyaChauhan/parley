import { ArrowLeft, ChevronLeft, ChevronRight, Folder } from "lucide-react"
import { Avatar } from "@/components/Avatar"
import { cn } from "@/lib/utils"
import { lastSeenText } from "./time"
import { tintFor, type ChatSummary } from "./types"

type SidePanelProps = {
  chat: ChatSummary
  open: boolean // 1280px and up: open, or folded to the strip
  onToggle: () => void
  onBack: () => void
  narrowVisible: boolean // below 1280px: it's the panel's turn instead of the conversation's
}

// The right panel: the open chat's name and member count, and its shared files.
// 1280px and up: a column of its own, which folds to a thin strip (reference-3).
// Below 1280px there's no room for it, so it takes the conversation's place when you
// tap the chat's name, with a back arrow to return (D8). On a phone that's a full screen.
export function SidePanel({ chat, open, onToggle, onBack, narrowVisible }: SidePanelProps) {
  const tint = tintFor(chat.id)

  return (
    <>
      <aside
        className={cn(
          "min-h-0 flex-1 flex-col overflow-y-auto overscroll-contain px-4 scrollbar-thin xl:w-85 xl:flex-none",
          narrowVisible ? "flex" : "hidden",
          open ? "xl:flex" : "xl:hidden",
        )}
      >
        <div className="relative flex flex-col items-center pt-6 pb-5">
          {/* Below 1280px: a back arrow to the conversation in the top-left corner, no header or title (D8) */}
          <button
            type="button"
            onClick={onBack}
            aria-label="Back to the conversation"
            className="absolute top-4 left-0 flex size-10 items-center justify-center rounded-lg bg-row-selected text-muted-foreground xl:hidden"
          >
            <ArrowLeft className="size-4" />
          </button>
          <button
            type="button"
            onClick={onToggle}
            aria-label="Fold the panel"
            className="absolute top-5 right-0 hidden size-8 items-center justify-center rounded-lg text-muted-foreground hover:bg-row-selected xl:flex"
          >
            <ChevronRight className="size-5" />
          </button>
          <Avatar name={chat.name} tint={tint} size="lg" />
          <p className="mt-2 max-w-full truncate px-10 text-name">{chat.name}</p>
          {/* A 1:1 chat: online or last seen, like the conversation header (D8). Groups come in v2. */}
          <p className="text-sm text-muted-foreground">
            {chat.kind !== "direct" ? "Group" : chat.online ? "online" : lastSeenText(chat.last_seen)}
          </p>
        </div>

        {/* No real files until v2 (D8) */}
        <div className="flex flex-col items-center gap-3 rounded-lg bg-row-selected px-4 py-10 text-center">
          <span className="flex size-12 items-center justify-center rounded-lg bg-accent text-primary">
            <Folder className="size-5" />
          </span>
          <p className="text-muted-foreground">No files yet</p>
        </div>
      </aside>

      {/* Folded, 1280px and up: just the open button and the avatar (D8) */}
      <aside className={cn("w-18 shrink-0 flex-col items-center", open ? "hidden" : "hidden xl:flex")}>
        <div className="flex w-full shrink-0 justify-center pt-5">
          <button
            type="button"
            onClick={onToggle}
            aria-label="Open the panel"
            className="flex size-8 items-center justify-center rounded-lg text-muted-foreground hover:bg-row-selected"
          >
            <ChevronLeft className="size-5" />
          </button>
        </div>
        <div className="mt-4">
          <Avatar name={chat.name} tint={tint} />
        </div>
      </aside>
    </>
  )
}
