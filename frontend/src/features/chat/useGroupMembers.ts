import { useEffect, useEffectEvent, useState } from "react"
import { api } from "@/lib/api"
import { useLiveEvents } from "@/lib/live"
import type { ChatSummary, GroupMember } from "./types"

// The open group's current members, for the header's names and the side panel
// (D37). Loaded when the group opens, and again after every group note in it
// (someone joined, left, or became admin). null = not a group, I left it, or
// still loading. setMembers takes the fresh list an admin's change answers with.
export function useGroupMembers(chat: ChatSummary | null) {
  // Kept with the group it belongs to, so another group never shows these people
  const [loaded, setLoaded] = useState<{ chatId: string; list: GroupMember[] } | null>(null)
  // Only a current member may see who's in it now
  const groupId = chat && chat.kind === "group" && !chat.left ? chat.id : null

  function load(chatId: string) {
    api<GroupMember[]>(`/chats/${chatId}/members`)
      .then((list) => setLoaded({ chatId, list }))
      .catch(() => {}) // the old list stays; the next note tries again
  }

  const loadFirst = useEffectEvent(load)
  useEffect(() => {
    if (groupId) loadFirst(groupId)
  }, [groupId])

  useLiveEvents((event) => {
    if (groupId && event.type === "message.new" && event.data.chat_id === groupId && event.data.kind === "system") {
      load(groupId)
    }
  })

  function setMembers(chatId: string, list: GroupMember[]) {
    setLoaded({ chatId, list })
  }

  return { members: groupId && loaded?.chatId === groupId ? loaded.list : null, setMembers }
}
