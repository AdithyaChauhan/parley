import { useEffect, useEffectEvent, useState } from "react"
import type { LiveEvent } from "@/features/chat/types"
import { api } from "./api"

// The live line to the server: one WebSocket per open tab (D19). The server
// pushes events down it; sending messages still goes over HTTP (D3).
// If the line drops, it reconnects by itself (D21).

let socket: WebSocket | null = null
// Everyone listening for pushed events (useLiveEvents)
const listeners = new Set<(event: LiveEvent) => void>()
// The highest message number this tab has, per chat (D20). Kept so it can be
// told again when the line opens: the chat list often loads before that.
const delivered = new Map<string, number>()
// The same for "read": the highest number shown on screen, per chat
const read = new Map<string, number>()
// When this tab last sent "typing", per chat (milliseconds)
const lastTyping = new Map<string, number>()

// The other side shows "typing..." for 5 s, so one every 3 s keeps it on while you type
const TYPING_EVERY_MS = 3000
// Heartbeat (D21): a ping every 25 s. No pong within 10 s means the line is dead.
const PING_EVERY_MS = 25_000
const PONG_WITHIN_MS = 10_000
// Reconnect waits 1 s, 2 s, 4 s ... up to 30 s, plus up to 1 s of random extra,
// so thousands of apps don't all call back in the same second (D21)
const FIRST_WAIT_MS = 1000
const LONGEST_WAIT_MS = 30_000
const RANDOM_EXTRA_MS = 1000

// connecting = the very first try, online = the line is open,
// reconnecting = it dropped (or never came) and we're trying again
export type LiveStatus = "connecting" | "online" | "reconnecting"

function send(type: string, data: object) {
  if (socket?.readyState === WebSocket.OPEN) socket.send(JSON.stringify({ type, data }))
}

// "This device has every message in this chat up to #seq" (D20).
// Only a higher number than before is sent; the server ignores anything else anyway.
export function reportDelivered(chatId: string, seq: number) {
  if (seq <= (delivered.get(chatId) ?? 0)) return
  delivered.set(chatId, seq)
  send("delivered", { chat_id: chatId, seq })
}

// "I've seen every message in this chat up to #seq, on screen" (D20). Only the
// open chat sends this, never the chat list. Read also counts as delivered on the server.
export function reportRead(chatId: string, seq: number) {
  if (seq <= (read.get(chatId) ?? 0)) return
  read.set(chatId, seq)
  send("read", { chat_id: chatId, seq })
}

// "I'm typing in this chat", at most once every 3 seconds. Never saved (D20).
export function sendTyping(chatId: string) {
  const now = Date.now()
  if (now - (lastTyping.get(chatId) ?? 0) < TYPING_EVERY_MS) return
  lastTyping.set(chatId, now)
  send("typing", { chat_id: chatId })
}

// The window is in front: its tab is showing and it has the keyboard focus.
// Only then can a message on screen count as read (D20).
export function windowInFront() {
  return document.visibilityState === "visible" && document.hasFocus()
}

// Hands an event to everyone listening. Pushed events come through here, and so
// does my send's reply (a saved message, like a pushed one), so the screen has
// one way in for both: the chat list, the gap check and "no doubles" work the same.
export function announce(event: LiveEvent) {
  for (const listener of listeners) listener(event)
}

// Calls handler for every announced event (pushed, or my send's reply), while the component is on screen.
// useEffectEvent: the handler always sees the latest state, without re-subscribing.
export function useLiveEvents(handler: (event: LiveEvent) => void) {
  const onEvent = useEffectEvent(handler)
  useEffect(() => {
    const listener = (event: LiveEvent) => onEvent(event)
    listeners.add(listener)
    return () => {
      listeners.delete(listener)
    }
  }, [])
}

// Opens the line while the screen using it is showing, and closes it for good
// when that screen goes away (log-out). If the line drops, it tries again by
// itself, with a new ticket each time (D21). Returns how the line is doing.
export function useLiveConnection() {
  const [status, setStatus] = useState<LiveStatus>("connecting")

  useEffect(() => {
    let line: WebSocket | null = null
    let trying = false // a ticket is on its way
    let stopped = false // log-out: never reconnect after this
    let failures = 0 // drops and failed tries since the last good connection: sets the next wait
    let retryTimer: number | undefined
    let pingTimer: number | undefined
    let pongTimer: number | undefined

    async function connect() {
      if (stopped || trying || line) return // already open, or on its way
      clearTimeout(retryTimer)
      trying = true
      try {
        // A new ticket every time: each one works once (D19). It costs a normal
        // request with the access token; the line itself can't carry one.
        const { ticket } = await api<{ ticket: string }>("/live/ticket", { method: "POST" })
        if (!stopped) open(ticket)
      } catch {
        lost() // backend down, or no network
      } finally {
        trying = false
      }
    }

    function open(ticket: string) {
      // Same site as the page, so it goes through the Vite proxy (later Nginx).
      const scheme = location.protocol === "https:" ? "wss" : "ws"
      const ws = new WebSocket(`${scheme}://${location.host}/api/live?ticket=${encodeURIComponent(ticket)}`)
      line = ws
      socket = ws
      // No hello within 10 s counts as a dead line too
      pongTimer = window.setTimeout(hangUp, PONG_WITHIN_MS)

      ws.onmessage = (message) => {
        const event = JSON.parse(message.data) as LiveEvent
        if (event.type === "pong") {
          clearTimeout(pongTimer) // still alive
          return
        }
        if (event.type === "hello") {
          // The server took our ticket: a good connection, so the next drop waits 1 s again
          clearTimeout(pongTimer)
          failures = 0
          setStatus("online")
          startHeartbeat()
          // Tell it what this tab already has
          for (const [chatId, seq] of delivered) send("delivered", { chat_id: chatId, seq })
          for (const [chatId, seq] of read) send("read", { chat_id: chatId, seq })
        }
        // hello goes to the listeners too: it's their cue to catch up (D21)
        announce(event)
      }
      // A bad ticket (4401), a server restart, or a network the browser knows is gone
      ws.onclose = lost
    }

    // The line is gone, or never came: go grey and try again after the wait
    function lost() {
      clearInterval(pingTimer)
      clearTimeout(pongTimer)
      line = null
      socket = null
      if (stopped) return
      setStatus("reconnecting")
      const wait = Math.min(FIRST_WAIT_MS * 2 ** failures, LONGEST_WAIT_MS) + Math.random() * RANDOM_EXTRA_MS
      failures += 1
      clearTimeout(retryTimer)
      retryTimer = window.setTimeout(connect, wait)
    }

    // Hang up ourselves: no pong came, or the browser says it's offline (D21).
    // A dead network can take minutes to confirm a close, so don't wait for onclose.
    function hangUp() {
      if (!line) return
      line.onclose = null
      line.onmessage = null
      line.close()
      lost()
    }

    // "Are you still there?" every 25 s. The pong clears the 10 s timer.
    function startHeartbeat() {
      pingTimer = window.setInterval(() => {
        send("ping", {})
        clearTimeout(pongTimer)
        pongTimer = window.setTimeout(hangUp, PONG_WITHIN_MS)
      }, PING_EVERY_MS)
    }

    // Skip the wait and try now: the network is back, or the tab is in front again (D21)
    const onOnline = () => connect()
    const onVisible = () => {
      if (document.visibilityState === "visible") connect()
    }
    window.addEventListener("online", onOnline)
    window.addEventListener("offline", hangUp)
    document.addEventListener("visibilitychange", onVisible)

    connect()

    return () => {
      stopped = true
      window.removeEventListener("online", onOnline)
      window.removeEventListener("offline", hangUp)
      document.removeEventListener("visibilitychange", onVisible)
      clearTimeout(retryTimer)
      clearInterval(pingTimer)
      clearTimeout(pongTimer)
      if (line) {
        line.onclose = null
        line.close()
      }
      socket = null
      // Someone else may log in next in this tab
      delivered.clear()
      read.clear()
      lastTyping.clear()
    }
  }, [])

  return status
}
