import { useEffect, useRef, useState } from "react"
import { Palette, SendHorizontal, X } from "lucide-react"
import { ApiError } from "@/lib/api"
import type { PreparedFile } from "@/lib/files"
import { cn } from "@/lib/utils"
import { postPhoto, postText } from "./statusApi"
import { STATUS_COLORS } from "./types"

const MAX_TEXT = 700

export type Draft = { kind: "text" } | { kind: "photo"; file: PreparedFile; localUrl: string }

function problemText(error: unknown) {
  if (error instanceof ApiError && error.status === 429) return "Too many statuses for now. Try again later."
  if (error instanceof ApiError && error.status === 0) return "No connection. Try again."
  return "Couldn't post it. Try again."
}

// A new status, full screen (D41): words on a colored background, or a photo
// with a caption. A failed post can be sent again with the same id, so it's
// never saved twice.
export function StatusComposer({
  draft,
  onClose,
  onPosted,
}: {
  draft: Draft
  onClose: () => void
  onPosted: () => void
}) {
  const [text, setText] = useState("")
  const [color, setColor] = useState(0)
  const [progress, setProgress] = useState<number | null>(null) // null = not sending
  const [problem, setProblem] = useState<string | null>(null)
  const id = useRef(crypto.randomUUID())
  const isText = draft.kind === "text"
  const ready = isText ? text.trim().length > 0 : true

  // Esc closes, unless it's on its way
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape" && progress === null) onClose()
    }
    document.addEventListener("keydown", onKey)
    return () => document.removeEventListener("keydown", onKey)
  }, [onClose, progress])

  async function post() {
    if (!ready || progress !== null) return
    setProblem(null)
    setProgress(0)
    try {
      if (draft.kind === "text") await postText(id.current, text.trim(), color)
      else await postPhoto(id.current, draft.file, text.trim(), setProgress)
      onPosted()
    } catch (error) {
      setProblem(problemText(error))
      setProgress(null)
    }
  }

  return (
    <div
      role="dialog"
      aria-label={isText ? "New text status" : "New photo status"}
      className="fixed inset-x-0 top-[var(--visible-top,0px)] z-50 flex h-[var(--visible-height,100dvh)] flex-col bg-black text-white"
      style={isText ? { backgroundColor: STATUS_COLORS[color] } : undefined}
    >
      <div className="flex shrink-0 items-center justify-between p-4">
        <button
          type="button"
          onClick={onClose}
          aria-label="Close"
          className="flex size-10 items-center justify-center rounded-full hover:bg-white/15"
        >
          <X className="size-6" />
        </button>
        {isText && (
          <button
            type="button"
            onClick={() => setColor((c) => (c + 1) % STATUS_COLORS.length)}
            aria-label="Change color"
            className="flex size-10 items-center justify-center rounded-full hover:bg-white/15"
          >
            <Palette className="size-6" />
          </button>
        )}
      </div>

      <div className="flex min-h-0 flex-1 items-center justify-center px-6">
        {isText ? (
          <textarea
            autoFocus
            value={text}
            maxLength={MAX_TEXT}
            onChange={(e) => setText(e.target.value)}
            placeholder="Type a status"
            aria-label="Status text"
            rows={4}
            className="w-full max-w-xl resize-none bg-transparent text-center text-3xl leading-snug outline-none placeholder:text-white/60"
          />
        ) : (
          <img src={draft.localUrl} alt="" className="max-h-full max-w-full rounded-lg object-contain" />
        )}
      </div>

      <div className="shrink-0 p-4">
        {problem && <p className="mb-2 text-center text-sm text-red-200">{problem}</p>}
        {progress !== null && !isText && (
          <div className="mx-auto mb-3 h-1 max-w-xl overflow-hidden rounded bg-white/25">
            <div className="h-full bg-white" style={{ width: `${Math.round(progress * 100)}%` }} />
          </div>
        )}
        <div className="mx-auto flex max-w-xl items-center gap-2">
          {!isText && (
            <input
              value={text}
              maxLength={MAX_TEXT}
              onChange={(e) => setText(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && post()}
              placeholder="Add a caption"
              aria-label="Caption"
              className="h-12 min-w-0 flex-1 rounded-full bg-white/15 px-5 text-base outline-none placeholder:text-white/60"
            />
          )}
          <button
            type="button"
            onClick={post}
            disabled={!ready || progress !== null}
            aria-label="Post status"
            className={cn(
              "ml-auto flex size-12 shrink-0 items-center justify-center rounded-full bg-primary text-primary-foreground",
              (!ready || progress !== null) && "opacity-50",
            )}
          >
            <SendHorizontal className="size-5" />
          </button>
        </div>
      </div>
    </div>
  )
}
