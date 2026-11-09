import { useEffect, useEffectEvent, useRef, useState } from "react"
import { chatsWithHistoryLeft, loadAllHistory, onCopyChanged, searchCopy, type Kept } from "@/lib/localCopy"
import type { ChatSummary } from "./types"

// Wait for a pause in the typing before searching
const TYPING_PAUSE_MS = 200

// What's on screen, and the words it was found with, for the highlight
type Found = { query: string; hits: Kept[]; more: boolean }

// Searches this device's copy (D40), in one chat or all of them. Searches again
// if the copy changes, so an edited or deleted message updates the results.
export function useSearch(query: string, chatId?: string) {
  const [found, setFound] = useState<Found | null>(null)
  const [version, setVersion] = useState(0)
  const wanted = query.trim()

  useEffect(() => onCopyChanged(() => setVersion((n) => n + 1)), [])

  useEffect(() => {
    if (!wanted) return
    let ignore = false
    const timer = window.setTimeout(() => {
      searchCopy(wanted, chatId).then((result) => {
        if (!ignore) setFound({ query: wanted, ...result })
      })
    }, TYPING_PAUSE_MS)
    return () => {
      ignore = true
      clearTimeout(timer)
    }
  }, [wanted, chatId, version])

  return wanted ? found : null
}

export type HistoryPhase = "checking" | "idle" | "loading" | "done" | "failed"
export type HistoryLoad = { phase: HistoryPhase; count: number; start: () => void; stop: () => void }

// The "Load all my history" button's state. Lives above both search boxes, so
// it keeps going while you move around.
export function useHistoryLoad(chats: ChatSummary[] | null): HistoryLoad {
  const [phase, setPhase] = useState<HistoryPhase>("checking")
  const [count, setCount] = useState(0)
  const stopping = useRef(false)

  // Is anything left? Asked again when a chat is added.
  const check = useEffectEvent(() => {
    if (!chats) return
    chatsWithHistoryLeft(chats).then((left) => {
      if (left === null) return
      setPhase((now) => (now === "loading" ? now : left > 0 ? "idle" : "done"))
    })
  })
  const chatCount = chats?.length ?? -1
  useEffect(() => {
    check()
  }, [chatCount])

  async function start() {
    if (!chats) return
    stopping.current = false
    setCount(0)
    setPhase("loading")
    const result = await loadAllHistory(chats, setCount, () => stopping.current)
    setPhase(result === "stopped" ? "idle" : result)
  }

  return {
    phase,
    count,
    start,
    stop: () => {
      stopping.current = true
    },
  }
}
