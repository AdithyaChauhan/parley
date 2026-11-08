import { useEffect, useRef, useState } from "react"
import { createPortal } from "react-dom"
import { Download, FileText, Pause, Play, X } from "lucide-react"
import { clockText, fileUrl, kindText, localUrlOf, saveFile, sizeText } from "@/lib/files"
import { cn } from "@/lib/utils"
import type { FileData, Message } from "./types"

// A link to the file, or null until it comes. Failed: the person may no longer be
// a member (D37), so whatever is already on screen stays.
function useFileLink(chatId: string, data: FileData, localUrl: string | undefined) {
  const [remote, setRemote] = useState<string | null>(null)
  const [failed, setFailed] = useState(false)
  const url = localUrl ?? localUrlOf(data.file_id)
  useEffect(() => {
    if (url) return
    let current = true
    fileUrl(chatId, data.file_id).then(
      (link) => current && setRemote(link),
      () => current && setFailed(true),
    )
    return () => {
      current = false
    }
  }, [chatId, data.file_id, url])
  return { url: url ?? remote, failed }
}

// A picture, large, over everything. Tap outside or press Esc to close it.
export function ImageViewer({ chatId, data, url, onClose }: { chatId: string; data: FileData; url: string; onClose: () => void }) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose()
    }
    window.addEventListener("keydown", onKey)
    return () => window.removeEventListener("keydown", onKey)
  }, [onClose])

  const button = "flex size-11 items-center justify-center rounded-lg bg-white/15 text-white hover:bg-white/25"
  return createPortal(
    <div
      role="dialog"
      aria-label={data.name}
      onClick={onClose}
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/85 p-4 pt-[max(4.5rem,env(safe-area-inset-top))]"
    >
      <div className="absolute top-[max(1rem,env(safe-area-inset-top))] right-4 flex gap-2">
        {data.file_id && (
          <button
            type="button"
            aria-label="Download"
            className={button}
            onClick={(e) => {
              e.stopPropagation()
              saveFile(chatId, data)
            }}
          >
            <Download className="size-5" />
          </button>
        )}
        <button type="button" aria-label="Close" className={button} onClick={onClose}>
          <X className="size-5" />
        </button>
      </div>
      <img src={url} alt={data.name} onClick={(e) => e.stopPropagation()} className="max-h-full max-w-full object-contain" />
    </div>,
    document.body,
  )
}

// How big a picture shows in its bubble. Its space is fixed from the start, so
// the list doesn't jump when the picture arrives.
function displaySize(data: FileData) {
  const width = data.width ?? 4
  const height = data.height ?? 3
  const shown = Math.max(120, Math.min(280, (320 * width) / height))
  // A real width: the bubble takes its size from this. max-width keeps it inside on a phone.
  return { width: Math.round(shown), maxWidth: "100%", aspectRatio: `${width} / ${height}` }
}

function ImageFile({ chatId, data, message }: { chatId: string; data: FileData; message: Message }) {
  const { url, failed } = useFileLink(chatId, data, message.localUrl)
  const [loaded, setLoaded] = useState(false)
  const [open, setOpen] = useState(false)
  return (
    <>
      <button
        type="button"
        onClick={() => url && !failed && setOpen(true)}
        aria-label={`Open ${data.name}`}
        style={displaySize(data)}
        className="relative block overflow-hidden rounded-lg bg-row-selected"
      >
        {data.preview && <img src={data.preview} alt="" className="absolute inset-0 size-full scale-110 object-cover blur-md" />}
        {url && (
          <img
            src={url}
            alt={data.name}
            loading="lazy"
            onLoad={() => setLoaded(true)}
            className={cn("absolute inset-0 size-full object-cover transition-opacity", loaded ? "opacity-100" : "opacity-0")}
          />
        )}
      </button>
      {open && url && <ImageViewer chatId={chatId} data={data} url={url} onClose={() => setOpen(false)} />}
    </>
  )
}

// Each kind of document keeps one color
const cardColors: Record<string, string> = {
  PDF: "bg-file-red text-file-red-icon",
  DOCX: "bg-file-purple text-file-purple-icon",
  XLSX: "bg-file-teal text-file-teal-icon",
  PPTX: "bg-file-yellow text-file-yellow-icon",
}

export function DocumentIcon({ data }: { data: FileData }) {
  return (
    <span
      className={cn(
        "flex size-11 shrink-0 items-center justify-center rounded-lg",
        cardColors[kindText(data)] ?? "bg-accent text-primary",
      )}
    >
      <FileText className="size-5" />
    </span>
  )
}

function DocumentFile({ chatId, data, message }: { chatId: string; data: FileData; message: Message }) {
  const [failed, setFailed] = useState(false)
  const saved = message.status === "sent"
  return (
    <div className="flex w-64 max-w-full items-center gap-3">
      <DocumentIcon data={data} />
      <div className="min-w-0 flex-1">
        <p className="truncate font-medium">{data.name}</p>
        <p className="text-label">{failed ? "Not available" : `${kindText(data)} · ${sizeText(data.size)}`}</p>
      </div>
      {saved && (
        <button
          type="button"
          aria-label={`Download ${data.name}`}
          onClick={() => saveFile(chatId, data).catch(() => setFailed(true))}
          className="flex size-10 shrink-0 items-center justify-center rounded-lg text-muted-foreground hover:bg-row-selected"
        >
          <Download className="size-5" />
        </button>
      )}
    </div>
  )
}

// Play and pause, how far along, and how long. The bars are the same for everyone:
// nobody's recording is analysed, the file is never opened on the server (D12).
export function VoicePlayer({ chatId, data, localUrl }: { chatId: string; data: FileData; localUrl?: string }) {
  const audio = useRef<HTMLAudioElement>(null)
  const [playing, setPlaying] = useState(false)
  const [position, setPosition] = useState(0) // in milliseconds
  const [failed, setFailed] = useState(false)
  const length = data.duration_ms ?? 0

  async function toggle() {
    const element = audio.current
    if (!element) return
    if (playing) {
      element.pause()
      return
    }
    try {
      // Asked for on the first press, so a long chat doesn't fetch every note
      if (!element.src) element.src = localUrl ?? localUrlOf(data.file_id) ?? (await fileUrl(chatId, data.file_id))
      await element.play()
    } catch {
      setFailed(true)
    }
  }

  return (
    <div className="flex w-60 max-w-full items-center gap-3">
      <audio
        ref={audio}
        preload="none"
        onPlay={() => setPlaying(true)}
        onPause={() => setPlaying(false)}
        onEnded={() => {
          setPlaying(false)
          setPosition(0)
        }}
        onTimeUpdate={(e) => setPosition(e.currentTarget.currentTime * 1000)}
      />
      <button
        type="button"
        aria-label={playing ? "Pause" : "Play voice note"}
        onClick={toggle}
        className="flex size-10 shrink-0 items-center justify-center rounded-full bg-primary text-primary-foreground"
      >
        {playing ? <Pause className="size-4" /> : <Play className="size-4" />}
      </button>
      <div className="h-1 min-w-0 flex-1 overflow-hidden rounded-full bg-foreground/15">
        <div
          className="h-full rounded-full bg-primary"
          style={{ width: `${length ? Math.min(100, (position / length) * 100) : 0}%` }}
        />
      </div>
      <span className="shrink-0 text-label tabular-nums">
        {failed ? "Not available" : clockText(position > 0 ? position : length)}
      </span>
    </div>
  )
}

// While it's on its way: how far it got, and a way to stop it
function UploadProgress({ message, onCancel }: { message: Message; onCancel: () => void }) {
  const percent = Math.round((message.progress ?? 0) * 100)
  return (
    <div className="mt-2 flex items-center gap-2">
      <div className="h-1 min-w-0 flex-1 overflow-hidden rounded-full bg-foreground/15">
        <div className="h-full rounded-full bg-primary transition-[width]" style={{ width: `${percent}%` }} />
      </div>
      <span className="text-label tabular-nums">{percent}%</span>
      <button
        type="button"
        onClick={onCancel}
        aria-label="Cancel upload"
        className="flex size-7 items-center justify-center rounded-md text-muted-foreground hover:bg-row-selected"
      >
        <X className="size-4" />
      </button>
    </div>
  )
}

// What goes inside the bubble of a file message
export function FileContent({ chatId, message, onCancel }: { chatId: string; message: Message; onCancel: () => void }) {
  const data = message.data as FileData
  const uploading = message.status === "sending" || message.status === "waiting"
  return (
    <div className="max-w-full">
      {data.category === "image" && <ImageFile chatId={chatId} data={data} message={message} />}
      {data.category === "document" && <DocumentFile chatId={chatId} data={data} message={message} />}
      {data.category === "voice" && <VoicePlayer chatId={chatId} data={data} localUrl={message.localUrl} />}
      {uploading && <UploadProgress message={message} onCancel={onCancel} />}
    </div>
  )
}
