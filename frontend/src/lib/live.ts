import { useEffect, useEffectEvent, useState } from "react"
import type { LiveEvent } from "@/features/chat/types"
import { api } from "./api"

// The live line to the server: one WebSocket per open tab (D19). The server
// pushes events down it; sending messages still goes over HTTP (D3).

let socket: WebSocket | null = null
// Everyone listening for pushed events (useLiveEvents)
const listeners = new Set<(event: LiveEvent) => void>()
// The highest message number this tab has, per chat (D20). Kept so it can be
// told again when the line opens: the chat list often loads before that.
const delivered = new Map<string, number>()

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

// Calls handler for every event the server pushes, while the component is on screen.
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

// Opens the line while the screen using it is showing, and closes it when that
// screen goes away (log-out). Returns true while the line is open.
// No auto-reconnect yet (T19): if the line drops, it stays closed until a reload.
export function useLiveConnection() {
  const [connected, setConnected] = useState(false)

  useEffect(() => {
    let line: WebSocket | null = null
    let stopped = false // the screen went away before the ticket came back

    async function open() {
      // The ticket costs a normal request with the access token; the line itself can't carry one.
      const { ticket } = await api<{ ticket: string }>("/live/ticket", { method: "POST" })
      if (stopped) return

      // Same site as the page, so it goes through the Vite proxy (later Nginx).
      const scheme = location.protocol === "https:" ? "wss" : "ws"
      line = new WebSocket(`${scheme}://${location.host}/api/live?ticket=${encodeURIComponent(ticket)}`)
      socket = line
      line.onmessage = (message) => {
        const event = JSON.parse(message.data) as LiveEvent
        if (event.type === "hello") {
          // The server took our ticket. Tell it what this tab already has.
          setConnected(true)
          for (const [chatId, seq] of delivered) send("delivered", { chat_id: chatId, seq })
          return
        }
        for (const listener of listeners) listener(event)
      }
      // Also fires for a bad ticket (code 4401) and when the backend stops.
      line.onclose = () => setConnected(false)
    }
    // Backend unreachable: no line, and the dot stays grey.
    open().catch(() => {})

    return () => {
      stopped = true
      line?.close()
      socket = null
      delivered.clear() // someone else may log in next in this tab
    }
  }, [])

  return connected
}
