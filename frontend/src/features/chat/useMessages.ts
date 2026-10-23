import { useEffect, useEffectEvent, useRef, useState } from "react"
import { api } from "@/lib/api"
import { reportDelivered, useLiveEvents } from "@/lib/live"
import { fromServer, type Message, type MessagePage, type ServerMessage } from "./types"

// Both lists together, each saved message once (matched by id), in number order
function merge(a: Message[], b: Message[]) {
  const byId = new Map([...a, ...b].map((message) => [message.id, message]))
  return [...byId.values()].sort((x, y) => (x.seq ?? 0) - (y.seq ?? 0))
}

// The highest number with no hole below it (D21). Usually the newest; lower if
// one in the middle is missing (I have #20 and #24, but not #21 to #23).
// Catch-up asks for everything after it, and "read" reports it.
function gapFree(saved: Message[]) {
  let upTo = saved[0]?.seq ?? 0
  for (const message of saved.slice(1)) {
    if (message.seq !== upTo + 1) break
    upTo += 1
  }
  return upTo
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

export function useMessages(chatId: string, myId: string, unsent: Message[], list: ListCheck) {
  const [saved, setSaved] = useState<Message[]>([])
  // The other person's bookmarks: my messages up to "delivered" get grey ✓✓, up to "read" teal ✓✓
  const [theirDelivered, setTheirDelivered] = useState(0)
  const [theirRead, setTheirRead] = useState(0)
  const [hasMore, setHasMore] = useState(false)
  const [loading, setLoading] = useState(true)
  const [failed, setFailed] = useState(false)
  const loadingOlder = useRef(false) // so fast scrolling doesn't ask for the same page twice
  const catchingUp = useRef(false) // one catch-up at a time, so a burst of pushes isn't a burst of requests

  // My unsent copy of a message that's saved already is hidden: the push can
  // arrive before my send's reply, and then the outbox still has it for a moment
  const savedIds = new Set(saved.map((message) => message.clientMsgId))
  const messages = [...saved, ...unsent.filter((message) => !savedIds.has(message.clientMsgId))]
  const gapFreeSeq = gapFree(saved)

  // A saved message for this chat: my send's reply, or one pushed live.
  // Never twice: the merge matches by id.
  function addSaved(message: ServerMessage) {
    setSaved((current) => merge(current, [fromServer(message)]))
  }

  // A page of saved messages in, from any direction. Merged, not replaced: a
  // message pushed while it loads must not be lost. Also takes the other
  // person's bookmarks, and tells the server the newest one is on this device.
  function takePage(page: MessagePage) {
    setSaved((current) => merge(page.messages.map(fromServer), current))
    const them = page.members.find((member) => member.user_id !== myId)
    setTheirDelivered((current) => Math.max(current, them?.delivered_up_to ?? 0))
    setTheirRead((current) => Math.max(current, them?.read_up_to ?? 0))
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
      if (event.data.sender_id !== myId) {
        const { seq } = event.data
        setTheirDelivered((current) => Math.max(current, seq))
        setTheirRead((current) => Math.max(current, seq))
      }
      // A hole: I have up to #20 and this is #23, so #21 and #22 went missing (D21)
      if (!loading && event.data.seq > gapFreeSeq + 1) catchUp(gapFreeSeq)
    }
    // The other person got or read more of my messages: redraw the ticks
    if (event.type === "receipt" && event.data.chat_id === chatId && event.data.user_id !== myId) {
      const { delivered_up_to: deliveredUpTo, read_up_to: readUpTo } = event.data
      setTheirDelivered((current) => Math.max(current, deliveredUpTo))
      setTheirRead((current) => Math.max(current, readUpTo))
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

  return { messages, gapFreeSeq, theirDelivered, theirRead, hasMore, loading, failed, loadOlder }
}
