import { useEffect, useEffectEvent, useRef, useState } from "react"
import { api } from "@/lib/api"
import { reportDelivered, useLiveEvents } from "@/lib/live"
import { fromServer, isEvent, type Message, type MessagePage, type ServerMessage } from "./types"

// Both lists together, each saved message once (matched by id), in number
// order. Of two copies, the one with the latest change wins (D39).
function merge(a: Message[], b: Message[]) {
  const byId = new Map<string | null, Message>()
  for (const message of [...a, ...b]) {
    const other = byId.get(message.id)
    if (!other || message.stateSeq >= other.stateSeq) byId.set(message.id, message)
  }
  return [...byId.values()].sort((x, y) => (x.seq ?? 0) - (y.seq ?? 0))
}

// Numbers this chat has settled, as [low, high] stretches, lowest first. A
// reaction, edit or delete has a number but no bubble (D39), so the saved
// messages alone would show holes where there are none.
type Stretch = [number, number]

// One more stretch, joined up with any it touches
function settle(stretches: Stretch[], low: number, high: number): Stretch[] {
  const joined: Stretch[] = []
  for (const [from, to] of [...stretches, [low, high] as Stretch].sort((x, y) => x[0] - y[0])) {
    const last = joined.at(-1)
    if (last && from <= last[1] + 1) last[1] = Math.max(last[1], to)
    else joined.push([from, to])
  }
  return joined
}

// The messages of one open chat, oldest at the top: saved ones by number,
// then my unsaved ones from the outbox (useOutbox). Loads the newest 30, loads
// older ones on request, takes in new messages and ticks pushed live (D20), and
// catches up on anything missed while the line was down (D21).
// The chat list's side of things, for the re-check below
type ListCheck = {
  seq: number // the newest number the chat list knows for this chat
  checks: number // goes up each time the chat list re-checks the server
  lineDown: boolean // the live line dropped or failed
}

// Each other current member's two bookmarks: user id → how far they got (D9)
type Bookmarks = Record<string, { delivered: number; read: number }>

// The lowest of everyone's bookmarks: a group message is delivered (or read)
// only once every other current member has it (D37). A direct chat has one
// other person, so it's just theirs. With nobody else, nothing gets ticks.
function lowest(bookmarks: Bookmarks, kind: "delivered" | "read") {
  const all = Object.values(bookmarks).map((member) => member[kind])
  return all.length ? Math.min(...all) : 0
}

// One person's bookmarks, moved forward only, and only for a current member:
// someone who left doesn't hold the ticks back, or come back through a late receipt
function raise(bookmarks: Bookmarks, userId: string, delivered: number, read: number): Bookmarks {
  const now = bookmarks[userId]
  if (!now || (delivered <= now.delivered && read <= now.read)) return bookmarks
  return { ...bookmarks, [userId]: { delivered: Math.max(now.delivered, delivered), read: Math.max(now.read, read) } }
}

export function useMessages(chatId: string, myId: string, unsent: Message[], list: ListCheck) {
  const [saved, setSaved] = useState<Message[]>([])
  const [settled, setSettled] = useState<Stretch[]>([])
  // The others' bookmarks: my messages up to the lowest "delivered" get grey ✓✓, up to the lowest "read" teal ✓✓
  const [bookmarks, setBookmarks] = useState<Bookmarks>({})
  // A group's lowest bookmarks, pushed by the server whenever they move (D37).
  // In a group, the others' own receipts don't come here any more (only their
  // own tabs get them), so this is what moves the ticks. Stays 0 in a direct chat.
  const [groupLow, setGroupLow] = useState({ delivered: 0, read: 0 })
  // Both are true "at least" numbers, so the higher one wins
  const theirDelivered = Math.max(lowest(bookmarks, "delivered"), groupLow.delivered)
  const theirRead = Math.max(lowest(bookmarks, "read"), groupLow.read)
  const [hasMore, setHasMore] = useState(false)
  const [loading, setLoading] = useState(true)
  const [failed, setFailed] = useState(false)
  const loadingOlder = useRef(false) // so fast scrolling doesn't ask for the same page twice
  const catchingUp = useRef(false) // one catch-up at a time, so a burst of pushes isn't a burst of requests

  // My unsent copy of a message that's saved already is hidden: the push can
  // arrive before my send's reply, and then the outbox still has it for a moment
  const savedIds = new Set(saved.map((message) => message.clientMsgId))
  const messages = [...saved, ...unsent.filter((message) => !savedIds.has(message.clientMsgId))]
  // The highest number with no hole below it (D21). Usually the newest; lower if
  // one in the middle is missing (I have #20 and #24, but not #21 to #23).
  // Catch-up asks for everything after it, and "read" reports it.
  const gapFreeSeq = settled[0]?.[1] ?? 0

  // A message changed (D39). Only ones already on screen: an older one comes
  // with its latest state when its page loads.
  function applyChange(target: ServerMessage) {
    setSaved((current) =>
      current.map((message) =>
        message.id === target.id && target.state_seq >= message.stateSeq ? fromServer(target) : message,
      ),
    )
  }

  // A saved message for this chat: my send's reply, or one pushed live.
  // Never twice: the merge matches by id. A change has no bubble of its own.
  function addSaved(message: ServerMessage) {
    setSettled((current) => settle(current, message.seq, message.seq))
    if (!isEvent(message)) setSaved((current) => merge(current, [fromServer(message)]))
    else if (message.target) applyChange(message.target)
  }

  // A page of saved messages in, from any direction. Merged, not replaced: a
  // message pushed while it loads must not be lost. Also takes the others'
  // bookmarks, and tells the server the newest one is on this device.
  // Every page lists the current members, so it also says who counts for the
  // ticks now: someone added or removed is picked up here (D37).
  function takePage(page: MessagePage) {
    setSaved((current) => merge(page.messages.filter((row) => !isEvent(row)).map(fromServer), current))
    // Only catch-up pages have changes in them
    for (const row of page.messages) if (row.target) applyChange(row.target)
    const { low_seq: low, high_seq: high } = page
    if (low !== null && high !== null) setSettled((current) => settle(current, low, high))
    setBookmarks((current) => {
      const next: Bookmarks = {}
      for (const member of page.members) {
        if (member.user_id === myId) continue
        const before = current[member.user_id]
        next[member.user_id] = {
          delivered: Math.max(before?.delivered ?? 0, member.delivered_up_to),
          read: Math.max(before?.read ?? 0, member.read_up_to),
        }
      }
      return next
    })
    const newest = Math.max(0, ...page.messages.map((message) => message.seq))
    if (newest > 0) reportDelivered(chatId, newest)
  }

  // The newest 30: when the chat opens, or on a hello if it never loaded (D21).
  function loadNewest() {
    api<MessagePage>(`/chats/${chatId}/messages`)
      .then((page) => {
        takePage(page)
        setHasMore(page.has_more)
        setFailed(false)
      })
      .catch(() => setFailed(true))
      .finally(() => setLoading(false))
  }

  const loadFirst = useEffectEvent(loadNewest)
  useEffect(() => {
    loadFirst()
  }, [chatId])

  // Everything after #after, oldest first, 100 at a time while there are more (D21)
  async function catchUp(after: number) {
    if (catchingUp.current) return
    catchingUp.current = true
    try {
      let more = true
      while (more) {
        const page = await api<MessagePage>(`/chats/${chatId}/messages?after=${after}&limit=100`)
        takePage(page)
        more = page.has_more
        after = page.messages.at(-1)?.seq ?? after
      }
    } catch {
      // Nothing changes. The next hello, or the next hole, tries again.
    } finally {
      catchingUp.current = false
    }
  }

  // Each time the chat list re-checks the server (every 60 s while a chat is
  // open), this chat re-checks too, with one request for either reason:
  //   - the list knows a newer message than this chat shows (D21), or
  //   - the live line is down, so nothing is pushed: the page also carries the
  //     other person's bookmarks, so my ticks move within a minute (D24).
  // Once the line is back, only the first reason is left: pushes do the rest.
  const recheck = useEffectEvent(() => {
    if (loading || failed) return
    if (list.seq > gapFreeSeq || list.lineDown) catchUp(gapFreeSeq)
  })
  useEffect(() => {
    // catchUp only changes state after it hears back from the server (after
    // its first await), but the lint rule can't see past the await.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    recheck()
  }, [list.checks])

  useLiveEvents((event) => {
    // On the line again: get what was missed while it was down (D21).
    // A chat that never loaded (or is still loading) loads the normal way instead.
    if (event.type === "hello") {
      if (loading || failed) loadNewest()
      else catchUp(gapFreeSeq)
    }
    if (event.type === "message.new" && event.data.chat_id === chatId) {
      addSaved(event.data)
      // Their message #N means their bookmarks are at #N too: sending counts as
      // reading, and the server moves them with no receipt (D20). Only for pushes;
      // history and catch-up pages carry the real bookmarks.
      // A change to a message moves nobody's bookmarks (D39).
      const { seq, sender_id: senderId } = event.data
      if (senderId !== myId && !isEvent(event.data)) setBookmarks((current) => raise(current, senderId, seq, seq))
      // A hole: I have up to #20 and this is #23, so #21 and #22 went missing (D21).
      // A group note: someone joined or left, and the next page brings the new
      // member list for the ticks (D37). Either way, one small catch-up.
      if (!loading && (seq > gapFreeSeq + 1 || event.data.kind === "system")) catchUp(gapFreeSeq)
    }
    // Someone got or read more of my messages: redraw the ticks
    if (event.type === "receipt" && event.data.chat_id === chatId && event.data.user_id !== myId) {
      const { user_id: userId, delivered_up_to: deliveredUpTo, read_up_to: readUpTo } = event.data
      setBookmarks((current) => raise(current, userId, deliveredUpTo, readUpTo))
    }
    // In a group: everyone has got (or read) more. Forward only.
    if (event.type === "group_receipt" && event.data.chat_id === chatId) {
      const { delivered_up_to: delivered, read_up_to: read } = event.data
      setGroupLow((current) => ({ delivered: Math.max(current.delivered, delivered), read: Math.max(current.read, read) }))
    }
  })

  // The 30 just above the oldest message on screen
  async function loadOlder() {
    const oldest = saved[0]
    if (!hasMore || !oldest || loadingOlder.current) return

    loadingOlder.current = true
    try {
      const page = await api<MessagePage>(`/chats/${chatId}/messages?before=${oldest.seq}`)
      takePage(page)
      setHasMore(page.has_more)
    } catch {
      // Nothing changes. Scrolling to the top again tries again.
    } finally {
      loadingOlder.current = false
    }
  }

  return { messages, gapFreeSeq, theirDelivered, theirRead, hasMore, loading, failed, loadOlder, applyChange }
}
