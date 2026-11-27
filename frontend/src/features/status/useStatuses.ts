import { useEffect, useState } from "react"
import { api } from "@/lib/api"
import { useLiveEvents } from "@/lib/live"
import type { StatusFeed } from "./types"

// Statuses run out on the server at their time. This re-checks the list once
// a minute, so one that ran out while the page was open disappears too.
const RECHECK_MS = 60_000

// The status list (D41). Loaded once, then again whenever the line says
// someone's statuses changed, and when the line comes back (it may have missed some).
export function useStatuses() {
  const [feed, setFeed] = useState<StatusFeed | null>(null) // null = still loading
  const [now, setNow] = useState(() => Date.now())

  function reload() {
    api<StatusFeed>("/status")
      .then((fresh) => {
        setFeed(fresh)
        setNow(Date.now())
      })
      .catch(() => {}) // a failure keeps the old list up
  }

  useEffect(() => {
    reload()
    const timer = window.setInterval(() => setNow(Date.now()), RECHECK_MS)
    return () => clearInterval(timer)
  }, [])

  useLiveEvents((event) => {
    if (event.type === "status" || event.type === "hello") reload()
  })

  // Only what hasn't run out yet, by this device's clock
  const live = feed && {
    mine: feed.mine.filter((s) => Date.parse(s.expires_at) > now),
    people: feed.people
      .map((p) => ({
        ...p,
        statuses: p.statuses.filter((s) => Date.parse(s.expires_at) > now),
      }))
      .filter((p) => p.statuses.length > 0),
  }

  // A status I just watched: its ring turns grey now, without waiting for the server
  function seen(statusId: string) {
    setFeed(
      (current) =>
        current && {
          ...current,
          people: current.people.map((person) => {
            if (!person.statuses.some((s) => s.id === statusId)) return person
            const statuses = person.statuses.map((s) => (s.id === statusId ? { ...s, viewed: true } : s))
            return {
              ...person,
              statuses,
              all_viewed: statuses.every((s) => s.viewed),
            }
          }),
        },
    )
  }

  return { feed: live, reload, seen }
}

export type Statuses = ReturnType<typeof useStatuses>
