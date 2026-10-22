import { useEffect, useState } from "react"
import { api } from "./api"

// The live line to the server: one WebSocket per open tab (D19). The server
// pushes events down it; sending messages still goes over HTTP (D3).

// Every event looks like { type, data } (D19).
type LiveEvent = { type: string; data: Record<string, unknown> }

// Opens the line while the screen using it is showing, and closes it when that
// screen goes away (log-out). Returns true while the line is open.
// No auto-reconnect yet (T19): if the line drops, it stays closed until a reload.
export function useLiveConnection() {
  const [connected, setConnected] = useState(false)

  useEffect(() => {
    let socket: WebSocket | null = null
    let stopped = false // the screen went away before the ticket came back

    async function open() {
      // The ticket costs a normal request with the access token; the line itself can't carry one.
      const { ticket } = await api<{ ticket: string }>("/live/ticket", { method: "POST" })
      if (stopped) return

      // Same site as the page, so it goes through the Vite proxy (later Nginx).
      const scheme = location.protocol === "https:" ? "wss" : "ws"
      socket = new WebSocket(`${scheme}://${location.host}/api/live?ticket=${encodeURIComponent(ticket)}`)
      socket.onmessage = (message) => {
        const event = JSON.parse(message.data) as LiveEvent
        // "hello" means the server took our ticket. Other events come in T17.
        if (event.type === "hello") setConnected(true)
      }
      // Also fires for a bad ticket (code 4401) and when the backend stops.
      socket.onclose = () => setConnected(false)
    }
    // Backend unreachable: no line, and the dot stays grey.
    open().catch(() => {})

    return () => {
      stopped = true
      socket?.close()
    }
  }, [])

  return connected
}
