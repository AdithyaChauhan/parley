import { useEffect, useRef, useState } from "react"
import { useLiveEvents } from "@/lib/live"

// How long "typing..." stays after the last typing event. Their app sends one
// every 3 s while they type, so it stays on until they stop.
const SHOW_FOR_MS = 5000

// Who is typing in each chat right now: chat id → their user id (D20).
// Shown for 5 s after their last "typing", or until their message arrives.
export function useTyping() {
  const [typing, setTyping] = useState<Record<string, string>>({})
  // chat id → the timer that will hide it
  const timers = useRef(new Map<string, number>())

  function stop(chatId: string) {
    clearTimeout(timers.current.get(chatId))
    timers.current.delete(chatId)
    setTyping((all) => {
      if (!(chatId in all)) return all
      const rest = { ...all }
      delete rest[chatId]
      return rest
    })
  }

  useLiveEvents((event) => {
    if (event.type === "typing") {
      const { chat_id: chatId, user_id: userId } = event.data
      // Another one came in: start the 5 s again
      clearTimeout(timers.current.get(chatId))
      timers.current.set(chatId, window.setTimeout(() => stop(chatId), SHOW_FOR_MS))
      setTyping((all) => ({ ...all, [chatId]: userId }))
    }
    // Their message arrived, so they've finished typing it
    if (event.type === "message.new" && typing[event.data.chat_id] === event.data.sender_id) {
      stop(event.data.chat_id)
    }
  })

  // The screen goes away (log-out): leave no timers running
  useEffect(() => {
    const all = timers.current
    return () => {
      for (const timer of all.values()) clearTimeout(timer)
    }
  }, [])

  return typing
}
