import { useEffect, useEffectEvent, useRef, useState, type PointerEvent } from "react"
import { ChevronLeft, ChevronRight, Eye, SendHorizontal, Trash2, X } from "lucide-react"
import { Avatar } from "@/components/Avatar"
import { listTime } from "@/features/chat/time"
import { tintFor } from "@/features/chat/types"
import { cn } from "@/lib/utils"
import { deleteStatus, markViewed, photoUrl, viewersOf } from "./statusApi"
import { STATUS_COLORS, type PersonStatuses, type StatusItem, type Viewer } from "./types"

// How long each status shows before the next one
const TEXT_MS = 5000
const PHOTO_MS = 6000
// A press shorter than this is a tap (move on); longer is a hold (pause)
const TAP_MS = 250

type ViewerProps = {
  people: PersonStatuses[] // watched in this order, one person after another
  start: number // which person to begin with
  myId: string
  onClose: () => void
  onSeen: (statusId: string) => void
  onReply: (person: PersonStatuses, status: StatusItem, text: string) => void
  onDeleted: () => void
}

// The first status I haven't seen yet, or the first one
function firstUnseen(person: PersonStatuses) {
  return Math.max(
    0,
    person.statuses.findIndex((s) => !s.viewed),
  )
}

// One status on screen: words on a color, or a photo (its tiny preview until it loads)
function StatusContent({
  status,
  onReady,
  onMissing,
}: {
  status: StatusItem
  onReady: () => void
  onMissing: () => void
}) {
  const [url, setUrl] = useState<string | null>(null)
  const isReady = useEffectEvent(onReady)
  const isMissing = useEffectEvent(onMissing)
  useEffect(() => {
    if (status.kind !== "image") {
      isReady()
      return
    }
    let ignore = false
    photoUrl(status.id).then(
      (link) => !ignore && setUrl(link),
      () => !ignore && isMissing(),
    )
    return () => {
      ignore = true
    }
  }, [status.id, status.kind])

  if (status.kind === "text") {
    return (
      <div
        className="flex size-full items-center justify-center p-8"
        style={{ backgroundColor: STATUS_COLORS[status.color] }}
      >
        <p className="text-center text-3xl leading-snug wrap-break-word whitespace-pre-wrap">{status.body}</p>
      </div>
    )
  }
  return (
    <div className="relative flex size-full items-center justify-center">
      {status.preview && !url && (
        <img src={status.preview} alt="" className="absolute inset-0 size-full object-contain blur-lg" />
      )}
      {url && (
        <img
          src={url}
          alt={status.body || "Photo status"}
          onLoad={onReady}
          onError={onMissing}
          className="relative max-h-full max-w-full object-contain"
        />
      )}
      {status.body && (
        <p className="absolute inset-x-0 bottom-0 bg-black/50 px-6 py-4 text-center wrap-break-word">{status.body}</p>
      )}
    </div>
  )
}

// Watching statuses, full screen (D41). Tap the right side for the next one,
// the left side for the one before, and hold to pause. Mine show who viewed
// them and can be deleted; other people's can be answered in our chat.
export function StatusViewer({ people: initial, start, myId, onClose, onSeen, onReply, onDeleted }: ViewerProps) {
  // A copy taken on opening, so a list reload can't move things while I watch
  const [people, setPeople] = useState(initial)
  const [who, setWho] = useState(start)
  const [index, setIndex] = useState(() => firstUnseen(initial[start]))
  const [elapsed, setElapsed] = useState(0)
  const [ready, setReady] = useState(false)
  const [missing, setMissing] = useState(false)
  const [holding, setHolding] = useState(false)
  const [typing, setTyping] = useState(false)
  const [reply, setReply] = useState("")
  const [sentNote, setSentNote] = useState(false)
  const [viewers, setViewers] = useState<Viewer[] | null>(null) // open "Viewed by" list
  const [confirming, setConfirming] = useState(false)
  const pressedAt = useRef(0)
  const spent = useRef(0) // time shown so far, for the clock below
  const told = useRef(new Set<string>())

  const person = people[who]
  const status = person?.statuses[index]
  const mine = person?.user_id === myId
  const duration = status?.kind === "image" ? PHOTO_MS : TEXT_MS
  const paused = !ready || holding || typing || viewers !== null || confirming

  function go(nextWho: number, nextIndex: number) {
    setWho(nextWho)
    setIndex(nextIndex)
    spent.current = 0
    setElapsed(0)
    setReady(false)
    setMissing(false)
    setSentNote(false)
  }

  function next() {
    if (index < person.statuses.length - 1) go(who, index + 1)
    else if (who < people.length - 1) go(who + 1, firstUnseen(people[who + 1]))
    else onClose()
  }

  function previous() {
    if (index > 0) go(who, index - 1)
    else if (who > 0) go(who - 1, people[who - 1].statuses.length - 1)
    else {
      spent.current = 0
      setElapsed(0)
    }
  }

  // Seen: told to the server once, and the ring turns grey at once
  useEffect(() => {
    if (!status || mine || status.viewed || told.current.has(status.id)) return
    told.current.add(status.id)
    markViewed(status.id)
    onSeen(status.id)
  }, [status, mine, onSeen])

  // The clock: moves while nothing pauses it, and moves on at the end
  const finished = useEffectEvent(() => next())
  useEffect(() => {
    if (paused) return
    let last = performance.now()
    let frame = requestAnimationFrame(function tick(at) {
      spent.current = Math.min(duration, spent.current + (at - last))
      last = at
      setElapsed(spent.current)
      if (spent.current >= duration) {
        finished()
        return
      }
      frame = requestAnimationFrame(tick)
    })
    return () => cancelAnimationFrame(frame)
  }, [paused, duration, who, index])

  // Keys: arrows move, Esc closes
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (typing) return
      if (e.key === "Escape") onClose()
      if (e.key === "ArrowRight") next()
      if (e.key === "ArrowLeft") previous()
    }
    document.addEventListener("keydown", onKey)
    return () => document.removeEventListener("keydown", onKey)
  })

  function pressStart(e: PointerEvent) {
    pressedAt.current = Date.now()
    setHolding(true)
    e.currentTarget.setPointerCapture(e.pointerId)
  }

  function pressEnd(e: PointerEvent<HTMLDivElement>) {
    setHolding(false)
    if (Date.now() - pressedAt.current > TAP_MS) return // it was a hold
    const box = e.currentTarget.getBoundingClientRect()
    if (e.clientX - box.left < box.width / 3) previous()
    else next()
  }

  async function openViewers() {
    setViewers([])
    try {
      setViewers(await viewersOf(status.id))
    } catch {
      setViewers(null)
    }
  }

  async function remove() {
    try {
      await deleteStatus(status.id)
    } catch {
      setConfirming(false)
      return
    }
    setConfirming(false)
    onDeleted()
    const left = person.statuses.filter((s) => s.id !== status.id)
    if (left.length === 0) {
      onClose()
      return
    }
    setPeople((all) => all.map((p, i) => (i === who ? { ...p, statuses: left } : p)))
    go(who, Math.min(index, left.length - 1))
  }

  function sendReply() {
    const text = reply.trim()
    if (!text) return
    onReply(person, status, text)
    setReply("")
    setSentNote(true)
    ;(document.activeElement as HTMLElement | null)?.blur()
  }

  if (!person || !status) return null

  return (
    <div
      role="dialog"
      aria-label={`${mine ? "My" : `${person.name}'s`} status`}
      className="fixed inset-x-0 top-[var(--visible-top,0px)] z-50 flex h-[var(--visible-height,100dvh)] justify-center bg-black text-white select-none"
    >
      {/* Arrows beside the status on a wide screen */}
      <button
        type="button"
        onClick={previous}
        aria-label="Previous status"
        className="hidden w-16 items-center justify-center text-white/60 hover:text-white md:flex"
      >
        <ChevronLeft className="size-8" />
      </button>

      <div className="relative flex w-full max-w-md flex-col">
        {/* One bar per status: full for watched, filling for this one */}
        <div className="absolute inset-x-0 top-0 z-10 bg-linear-to-b from-black/60 to-transparent px-3 pt-3 pb-6">
          <div className="flex gap-1">
            {person.statuses.map((s, i) => (
              <div key={s.id} className="h-0.75 flex-1 overflow-hidden rounded bg-white/35">
                <div
                  className="h-full bg-white"
                  style={{
                    width: i < index ? "100%" : i === index ? `${(elapsed / duration) * 100}%` : "0%",
                  }}
                />
              </div>
            ))}
          </div>
          <div className="mt-3 flex items-center gap-3">
            <Avatar name={person.name} tint={mine ? "teal" : tintFor(person.user_id)} size="sm" />
            <div className="min-w-0 flex-1">
              <p className="truncate font-medium">{mine ? "My status" : person.name}</p>
              <p className="text-label text-white/75">{listTime(status.posted_at)}</p>
            </div>
            {mine && (
              <button
                type="button"
                onClick={() => setConfirming(true)}
                aria-label="Delete status"
                className="flex size-10 items-center justify-center rounded-full hover:bg-white/15"
              >
                <Trash2 className="size-5" />
              </button>
            )}
            <button
              type="button"
              onClick={onClose}
              aria-label="Close"
              className="flex size-10 items-center justify-center rounded-full hover:bg-white/15"
            >
              <X className="size-6" />
            </button>
          </div>
        </div>

        {/* Tap or hold anywhere on the status itself */}
        <div
          className="min-h-0 flex-1 touch-none"
          onPointerDown={pressStart}
          onPointerUp={pressEnd}
          onPointerCancel={() => setHolding(false)}
          onContextMenu={(e) => e.preventDefault()}
        >
          {missing ? (
            <div className="flex size-full items-center justify-center text-white/75">
              This status is no longer available
            </div>
          ) : (
            <StatusContent
              key={status.id}
              status={status}
              onReady={() => setReady(true)}
              onMissing={() => {
                setMissing(true)
                setReady(true)
              }}
            />
          )}
        </div>

        <div className="shrink-0 p-3">
          {mine ? (
            <button
              type="button"
              onClick={openViewers}
              className="mx-auto flex items-center gap-2 rounded-full px-4 py-2 hover:bg-white/15"
            >
              <Eye className="size-5" />
              {status.views === 1 ? "1 view" : `${status.views ?? 0} views`}
            </button>
          ) : (
            <>
              {sentNote && (
                <p className="mb-2 text-center text-sm text-white/75">Sent to your chat with {person.name}</p>
              )}
              <div className="flex items-center gap-2">
                <input
                  value={reply}
                  onChange={(e) => setReply(e.target.value)}
                  onFocus={() => setTyping(true)}
                  onBlur={() => setTyping(false)}
                  onKeyDown={(e) => e.key === "Enter" && sendReply()}
                  placeholder={`Reply to ${person.name}`}
                  aria-label="Reply"
                  maxLength={4000}
                  className="h-12 min-w-0 flex-1 rounded-full bg-white/15 px-5 text-base outline-none placeholder:text-white/60"
                />
                <button
                  type="button"
                  // Keeps the box focused while the button is pressed, so its blur doesn't restart the clock first
                  onPointerDown={(e) => e.preventDefault()}
                  onClick={sendReply}
                  disabled={!reply.trim()}
                  aria-label="Send reply"
                  className={cn(
                    "flex size-12 shrink-0 items-center justify-center rounded-full bg-primary text-primary-foreground",
                    !reply.trim() && "opacity-50",
                  )}
                >
                  <SendHorizontal className="size-5" />
                </button>
              </div>
            </>
          )}
        </div>

        {/* "Viewed by": a sheet over the bottom of the status */}
        {viewers !== null && (
          <div className="absolute inset-x-0 bottom-0 z-20 max-h-[60%] overflow-y-auto rounded-t-panel bg-card p-4 text-foreground">
            <div className="mb-2 flex items-center justify-between">
              <h2 className="font-medium">Viewed by {viewers.length}</h2>
              <button
                type="button"
                onClick={() => setViewers(null)}
                aria-label="Close viewers"
                className="flex size-8 items-center justify-center rounded-lg hover:bg-row-selected"
              >
                <X className="size-5" />
              </button>
            </div>
            {viewers.length === 0 && <p className="py-4 text-sm text-muted-foreground">No views yet</p>}
            {viewers.map((viewer) => (
              <div key={viewer.user_id} className="flex items-center gap-3 py-2">
                <Avatar name={viewer.name} tint={tintFor(viewer.user_id)} size="sm" />
                <span className="min-w-0 flex-1 truncate">{viewer.name}</span>
                <span className="text-label text-muted-foreground">{listTime(viewer.viewed_at)}</span>
              </div>
            ))}
          </div>
        )}

        {confirming && (
          <div className="absolute inset-x-0 bottom-0 z-20 rounded-t-panel bg-card p-4 text-foreground">
            <p className="mb-3">Delete this status for everyone?</p>
            <div className="flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setConfirming(false)}
                className="rounded-lg px-4 py-2 hover:bg-row-selected"
              >
                Cancel
              </button>
              <button type="button" onClick={remove} className="rounded-lg bg-destructive px-4 py-2 text-white">
                Delete
              </button>
            </div>
          </div>
        )}
      </div>

      <button
        type="button"
        onClick={next}
        aria-label="Next status"
        className="hidden w-16 items-center justify-center text-white/60 hover:text-white md:flex"
      >
        <ChevronRight className="size-8" />
      </button>
    </div>
  )
}
