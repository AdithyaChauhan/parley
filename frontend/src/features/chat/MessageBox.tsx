import { useRef, useState, type FormEvent, type PointerEvent } from "react"
import { Check, Mic, Paperclip, SendHorizontal, X } from "lucide-react"
import { Button } from "@/components/ui/button"
import { ACCEPTED_FILES, clockText, type PreparedFile } from "@/lib/files"
import { canRecord, useVoiceRecorder } from "./useVoiceRecorder"

type MessageBoxProps = {
  onSend: (text: string) => void
  onTyping: () => void // called on every key; live.ts sends at most one "typing" every 3 s
  onFiles: (files: File[]) => void // picked with the attach button
  onVoice: (voice: PreparedFile) => void
  onHint: (text: string) => void
}

// Slide this far from the mic while holding, and letting go throws the recording away
const CANCEL_DISTANCE_PX = 90

// Stands in for the message box while I fix a message I sent (D39)
export function EditBox({
  original,
  onSave,
  onCancel,
}: {
  original: string
  onSave: (text: string) => void
  onCancel: () => void
}) {
  const [text, setText] = useState(original)

  function handleSubmit(e: FormEvent) {
    e.preventDefault()
    const trimmed = text.trim()
    if (!trimmed) return
    if (trimmed === original) onCancel()
    else onSave(trimmed)
  }

  return (
    <form
      onSubmit={handleSubmit}
      onKeyDown={(e) => e.key === "Escape" && onCancel()}
      className="flex h-16 items-center gap-2 rounded-panel bg-card pr-2 pl-2 shadow-sm shadow-foreground/5 md:gap-3 md:pl-3"
    >
      <button
        type="button"
        onClick={onCancel}
        aria-label="Cancel editing"
        className="flex size-10 shrink-0 items-center justify-center rounded-lg text-muted-foreground hover:bg-row-selected"
      >
        <X className="size-5" />
      </button>
      <div className="min-w-0 flex-1">
        <p className="text-xs leading-tight text-primary">Editing</p>
        <input
          value={text}
          onChange={(e) => setText(e.target.value)}
          autoFocus
          maxLength={4000}
          aria-label="Edit your message"
          // 16px on a phone, like the message box
          className="w-full bg-transparent text-base text-ellipsis outline-none md:text-body"
        />
      </div>
      <Button type="submit" aria-label="Save" disabled={!text.trim()} className="ml-1 size-12 shrink-0 rounded-lg md:ml-2">
        <Check className="size-5" />
      </Button>
    </form>
  )
}

// The white box at the bottom: attach, type a message, then the teal button.
// With nothing typed, the teal button is the mic: hold to record a voice note.
export function MessageBox({ onSend, onTyping, onFiles, onVoice, onHint }: MessageBoxProps) {
  const [text, setText] = useState("")
  const picker = useRef<HTMLInputElement>(null)
  const voice = useVoiceRecorder(onVoice, onHint)
  const [cancelling, setCancelling] = useState(false)
  const pressedAt = useRef({ x: 0, y: 0 })
  const showMic = !text.trim() && canRecord()

  function handleSubmit(e: FormEvent) {
    e.preventDefault() // stop the browser reloading the page
    const trimmed = text.trim()
    if (!trimmed) return
    onSend(trimmed)
    setText("")
  }

  function pressMic(e: PointerEvent<HTMLButtonElement>) {
    e.preventDefault()
    // Keeps the release coming here, even if the finger slides off the button
    e.currentTarget.setPointerCapture(e.pointerId)
    pressedAt.current = { x: e.clientX, y: e.clientY }
    setCancelling(false)
    voice.start()
  }

  function moveMic(e: PointerEvent<HTMLButtonElement>) {
    const moved = Math.hypot(e.clientX - pressedAt.current.x, e.clientY - pressedAt.current.y)
    setCancelling(moved > CANCEL_DISTANCE_PX)
  }

  function releaseMic() {
    if (cancelling) voice.cancel()
    else voice.stop()
    setCancelling(false)
  }

  return (
    <form
      onSubmit={handleSubmit}
      // Tighter on a phone, so the typing space keeps its room
      className="flex h-16 items-center gap-2 rounded-panel bg-card pr-2 pl-2 shadow-sm shadow-foreground/5 md:gap-3 md:pl-3"
    >
      {voice.recording ? (
        <p className="flex min-w-0 flex-1 items-center gap-3 pl-2" role="status">
          <span className="size-2.5 shrink-0 animate-pulse rounded-full bg-destructive" />
          <span className="text-body tabular-nums">{clockText(voice.elapsed)}</span>
          <span className="truncate text-sm text-muted-foreground">
            {cancelling ? "Let go to cancel" : "Let go to send, slide away to cancel"}
          </span>
        </p>
      ) : (
        <>
          <input
            ref={picker}
            type="file"
            multiple
            accept={ACCEPTED_FILES}
            hidden
            onChange={(e) => {
              onFiles([...(e.target.files ?? [])])
              e.target.value = "" // so picking the same file again still counts
            }}
          />
          <button
            type="button"
            onClick={() => picker.current?.click()}
            aria-label="Attach a file"
            className="flex size-10 shrink-0 items-center justify-center rounded-lg text-muted-foreground hover:bg-row-selected"
          >
            <Paperclip className="size-5" />
          </button>
          <input
            value={text}
            onChange={(e) => {
              setText(e.target.value)
              if (e.target.value.trim()) onTyping() // deleting everything isn't typing
            }}
            placeholder="Write your message..."
            aria-label="Message"
            // 16px on a phone: an iPhone zooms the whole page when you tap a smaller box
            className="min-w-0 flex-1 bg-transparent text-base text-ellipsis outline-none placeholder:text-muted-foreground md:text-body"
          />
        </>
      )}
      {showMic ? (
        <Button
          type="button"
          aria-label="Hold to record a voice note"
          onPointerDown={pressMic}
          onPointerMove={moveMic}
          onPointerUp={releaseMic}
          onPointerCancel={() => voice.cancel()}
          onContextMenu={(e) => e.preventDefault()} // a long press mustn't open the phone's menu
          className="ml-1 size-12 shrink-0 touch-none rounded-lg select-none md:ml-2"
        >
          <Mic className="size-5" />
        </Button>
      ) : (
        <Button type="submit" aria-label="Send" className="ml-1 size-12 shrink-0 rounded-lg md:ml-2">
          <SendHorizontal className="size-5" />
        </Button>
      )}
    </form>
  )
}
