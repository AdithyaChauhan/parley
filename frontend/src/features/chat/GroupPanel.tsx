import { useState, type FormEvent } from "react"
import { LogOut, MoreVertical, Pencil, UserPlus } from "lucide-react"
import { Avatar } from "@/components/Avatar"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { api } from "@/lib/api"
import { AddPeopleBox } from "./GroupBoxes"
import { groupError } from "./groupNotes"
import { tintFor, type ChatSummary, type GroupMember } from "./types"

// A group's part of the side panel (D37): its name (an admin can rename it),
// its members, and what you can do there. Admins add, remove and make admin;
// everyone can leave. Every change is checked again on the server.

type GroupPanelProps = {
  chat: ChatSummary
  chats: ChatSummary[] // my direct chats are who can be added
  myId: string
  members: GroupMember[] | null
  onMembersChanged: (members: GroupMember[]) => void // an admin's change answers with the new list
  onChatChanged: (chat: ChatSummary) => void // renamed, or I left: my chat-list row changed
}

// The name under the big avatar, and a pencil for admins to rename it
export function GroupName({ chat, onChatChanged }: Pick<GroupPanelProps, "chat" | "onChatChanged">) {
  const [editing, setEditing] = useState(false)
  const [name, setName] = useState(chat.name)
  const [error, setError] = useState("")
  const [busy, setBusy] = useState(false)
  const admin = chat.role === "admin" && !chat.left

  async function save(e: FormEvent) {
    e.preventDefault()
    if (!name.trim()) return setError("Give the group a name.")
    setBusy(true)
    setError("")
    try {
      onChatChanged(await api<ChatSummary>(`/chats/${chat.id}`, { method: "PATCH", body: { name: name.trim() } }))
      setEditing(false)
    } catch (err) {
      setError(groupError(err))
    } finally {
      setBusy(false)
    }
  }

  if (editing) {
    return (
      <form onSubmit={save} onKeyDown={(e) => e.key === "Escape" && setEditing(false)} className="mt-2 w-full px-2">
        <Input value={name} onChange={(e) => setName(e.target.value)} maxLength={50} autoFocus aria-label="Group name" />
        {error && <p className="mt-1.5 text-sm text-destructive">{error}</p>}
        <div className="mt-2 flex justify-center gap-2">
          <Button type="button" variant="ghost" size="sm" onClick={() => setEditing(false)}>
            Cancel
          </Button>
          <Button type="submit" size="sm" disabled={busy}>
            Save
          </Button>
        </div>
      </form>
    )
  }

  return (
    <div className="mt-2 flex max-w-full items-center gap-1 px-10">
      <p className="truncate text-name">{chat.name}</p>
      {admin && (
        <button
          type="button"
          onClick={() => {
            setName(chat.name)
            setEditing(true)
          }}
          aria-label="Rename the group"
          className="flex size-7 shrink-0 items-center justify-center rounded-lg text-muted-foreground hover:bg-row-selected"
        >
          <Pencil className="size-3.5" />
        </button>
      )}
    </div>
  )
}

// One person in the list. An admin can open the actions for anyone else.
function MemberRow({
  chatId,
  member,
  myId,
  canManage,
  onMembersChanged,
}: {
  chatId: string
  member: GroupMember
  myId: string
  canManage: boolean
  onMembersChanged: (members: GroupMember[]) => void
}) {
  const [open, setOpen] = useState(false)
  const [error, setError] = useState("")
  const [busy, setBusy] = useState(false)
  const me = member.user_id === myId

  async function act(path: string, method: string) {
    setBusy(true)
    setError("")
    try {
      onMembersChanged(await api<GroupMember[]>(`/chats/${chatId}/members/${member.user_id}${path}`, { method }))
      setOpen(false)
    } catch (err) {
      setError(groupError(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <li>
      <div className="flex items-center gap-3 py-2">
        <Avatar name={member.name} tint={tintFor(member.user_id)} size="sm" />
        <span className="min-w-0 flex-1 truncate text-sm">{me ? "You" : member.name}</span>
        {member.role === "admin" && (
          <span className="shrink-0 rounded-full bg-accent px-2 py-0.5 text-[11px] text-primary">Admin</span>
        )}
        {canManage && !me && (
          <button
            type="button"
            onClick={() => setOpen((o) => !o)}
            aria-label={`Actions for ${member.name}`}
            aria-expanded={open}
            className="flex size-7 shrink-0 items-center justify-center rounded-lg text-muted-foreground hover:bg-row-selected"
          >
            <MoreVertical className="size-4" />
          </button>
        )}
      </div>
      {/* Opens under the row, not as a popover: the panel scrolls and would cut one off */}
      {open && (
        <div className="mb-2 flex flex-col rounded-lg bg-card p-1 ring-1 ring-border">
          {member.role !== "admin" && (
            <button
              type="button"
              disabled={busy}
              onClick={() => act("/admin", "POST")}
              className="rounded-md px-3 py-2 text-left text-sm hover:bg-row-selected"
            >
              Make group admin
            </button>
          )}
          <button
            type="button"
            disabled={busy}
            onClick={() => act("", "DELETE")}
            className="rounded-md px-3 py-2 text-left text-sm text-destructive hover:bg-row-selected"
          >
            Remove {member.name}
          </button>
        </div>
      )}
      {error && <p className="mb-2 text-sm text-destructive">{error}</p>}
    </li>
  )
}

// The members and the actions, under the name. Someone who left sees none of it.
export function GroupMembers({ chat, chats, myId, members, onMembersChanged, onChatChanged }: GroupPanelProps) {
  const [adding, setAdding] = useState(false)
  const [confirmLeave, setConfirmLeave] = useState(false)
  const [error, setError] = useState("")
  const [busy, setBusy] = useState(false)
  const admin = chat.role === "admin"

  if (chat.left) return null

  async function leave() {
    setBusy(true)
    setError("")
    try {
      onChatChanged(await api<ChatSummary>(`/chats/${chat.id}/leave`, { method: "POST" }))
    } catch (err) {
      setError(groupError(err))
      setBusy(false)
    }
  }

  return (
    <div className="mb-4 flex flex-col">
      <div className="flex items-center justify-between">
        <h2>Members</h2>
        {admin && (
          <button
            type="button"
            onClick={() => setAdding((a) => !a)}
            aria-expanded={adding}
            className="flex items-center gap-1.5 rounded-lg px-2 py-1 text-sm text-primary hover:bg-accent"
          >
            <UserPlus className="size-4" />
            Add people
          </button>
        )}
      </div>
      {adding && members && (
        <AddPeopleBox
          chatId={chat.id}
          chats={chats}
          members={members}
          onAdded={(list) => {
            setAdding(false)
            onMembersChanged(list)
          }}
          onClose={() => setAdding(false)}
        />
      )}
      {members ? (
        <ul className="mt-1">
          {members.map((member) => (
            <MemberRow
              key={member.user_id}
              chatId={chat.id}
              member={member}
              myId={myId}
              canManage={admin}
              onMembersChanged={onMembersChanged}
            />
          ))}
        </ul>
      ) : (
        <p className="py-3 text-sm text-muted-foreground">Loading members...</p>
      )}

      {confirmLeave ? (
        <div className="mt-2 rounded-lg bg-card p-3 ring-1 ring-border">
          <p className="text-sm">Leave "{chat.name}"? You'll keep the messages you have.</p>
          <div className="mt-3 flex justify-end gap-2">
            <Button type="button" variant="ghost" size="sm" onClick={() => setConfirmLeave(false)}>
              Cancel
            </Button>
            <Button type="button" variant="destructive" size="sm" disabled={busy} onClick={leave}>
              Leave group
            </Button>
          </div>
        </div>
      ) : (
        <button
          type="button"
          onClick={() => setConfirmLeave(true)}
          className="mt-2 flex items-center gap-2 rounded-lg px-2 py-2 text-sm text-destructive hover:bg-row-selected"
        >
          <LogOut className="size-4" />
          Leave group
        </button>
      )}
      {error && <p className="mt-1 text-sm text-destructive">{error}</p>}
    </div>
  )
}
