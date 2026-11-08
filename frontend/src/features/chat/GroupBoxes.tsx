import { useState, type FormEvent } from "react"
import { X } from "lucide-react"
import { Avatar } from "@/components/Avatar"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { checkEmail } from "@/features/auth/validate"
import { api } from "@/lib/api"
import { groupError } from "./groupNotes"
import { tintFor, type ChatSummary, type GroupMember } from "./types"

// The two small boxes for groups (D37): "New group" from the "..." menu, and
// "Add people" in a group's side panel. Both pick people the same way: from
// your direct chats, or by exact email. There's no search or directory.

// Who can be picked: the people from my direct chats, minus anyone already in
type Pickable = { userId: string; name: string; chatId: string }

function pickable(chats: ChatSummary[], skip: GroupMember[] = []) {
  const already = new Set(skip.map((member) => member.user_id))
  return chats
    .filter((chat) => chat.kind === "direct" && chat.other_user_id && !already.has(chat.other_user_id))
    .map((chat) => ({ userId: chat.other_user_id!, name: chat.name, chatId: chat.id }))
    .sort((a, b) => a.name.localeCompare(b.name))
}

type Picked = { userIds: string[]; emails: string[] }

// Tick people from your chats, and/or type emails one at a time
function PeoplePicker({ people, picked, onChange }: { people: Pickable[]; picked: Picked; onChange: (p: Picked) => void }) {
  const [email, setEmail] = useState("")
  const [error, setError] = useState("")

  function toggle(userId: string) {
    const has = picked.userIds.includes(userId)
    onChange({ ...picked, userIds: has ? picked.userIds.filter((id) => id !== userId) : [...picked.userIds, userId] })
  }

  function addEmail() {
    const problem = checkEmail(email) // catches "ben@" before the server sends a 422
    if (problem) {
      setError(problem)
      return
    }
    const clean = email.trim().toLowerCase()
    if (!picked.emails.includes(clean)) onChange({ ...picked, emails: [...picked.emails, clean] })
    setEmail("")
    setError("")
  }

  return (
    <div className="mt-3">
      <p className="text-label">From your chats</p>
      {people.length === 0 ? (
        <p className="mt-1 text-sm text-muted-foreground">Nobody else from your chats.</p>
      ) : (
        <ul className="-mx-1 mt-1 max-h-44 overflow-y-auto scrollbar-thin">
          {people.map((person) => (
            <li key={person.userId}>
              <label className="flex cursor-pointer items-center gap-3 rounded-md px-1 py-1.5 hover:bg-row-selected">
                <input
                  type="checkbox"
                  checked={picked.userIds.includes(person.userId)}
                  onChange={() => toggle(person.userId)}
                  className="size-4 accent-primary"
                />
                <Avatar name={person.name} tint={tintFor(person.chatId)} size="sm" />
                <span className="truncate text-sm">{person.name}</span>
              </label>
            </li>
          ))}
        </ul>
      )}

      <label htmlFor="group-email" className="mt-3 block text-label">
        Or add by email
      </label>
      <div className="mt-1 flex gap-2">
        <Input
          id="group-email"
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          // Enter adds the email to the list, instead of sending the whole form
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault()
              addEmail()
            }
          }}
          placeholder="name@example.com"
          aria-invalid={error !== ""}
        />
        <Button type="button" variant="secondary" size="sm" onClick={addEmail} className="h-8">
          Add
        </Button>
      </div>
      {error && <p className="mt-1.5 text-sm text-destructive">{error}</p>}
      {picked.emails.length > 0 && (
        <ul className="mt-2 flex flex-wrap gap-1.5">
          {picked.emails.map((address) => (
            <li key={address} className="flex max-w-full items-center gap-1 rounded-full bg-accent py-0.5 pr-1 pl-2.5 text-xs">
              <span className="truncate">{address}</span>
              <button
                type="button"
                onClick={() => onChange({ ...picked, emails: picked.emails.filter((e) => e !== address) })}
                aria-label={`Remove ${address}`}
                className="flex size-4 items-center justify-center rounded-full text-muted-foreground hover:text-foreground"
              >
                <X className="size-3" />
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

// A popover box, the same as the "+" box (NewChatBox)
const boxClass =
  "absolute top-full right-0 z-20 mt-1 w-80 max-w-[calc(100vw-2rem)] rounded-lg bg-card p-3 text-left shadow-lg ring-1 shadow-foreground/10 ring-border"

type NewGroupBoxProps = {
  chats: ChatSummary[]
  onCreated: (chat: ChatSummary) => void
  onClose: () => void
}

// "New group": a name, plus people. The reply is a chat-list row, so it can go straight into the list.
export function NewGroupBox({ chats, onCreated, onClose }: NewGroupBoxProps) {
  const [name, setName] = useState("")
  const [picked, setPicked] = useState<Picked>({ userIds: [], emails: [] })
  const [error, setError] = useState("")
  const [busy, setBusy] = useState(false)
  const count = picked.userIds.length + picked.emails.length

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    if (!name.trim()) return setError("Give the group a name.")
    if (count === 0) return setError("Pick at least one person.")

    setBusy(true)
    setError("")
    try {
      const body = { name: name.trim(), user_ids: picked.userIds, emails: picked.emails }
      onCreated(await api<ChatSummary>("/chats/groups", { method: "POST", body }))
    } catch (err) {
      setError(groupError(err))
      setBusy(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} onKeyDown={(e) => e.key === "Escape" && onClose()} noValidate className={boxClass}>
      <label htmlFor="group-name" className="text-label">
        Group name
      </label>
      <Input
        id="group-name"
        value={name}
        onChange={(e) => setName(e.target.value)}
        maxLength={50}
        placeholder="Weekend trip"
        autoFocus
        className="mt-1"
      />
      <PeoplePicker people={pickable(chats)} picked={picked} onChange={setPicked} />
      {error && <p className="mt-2 text-sm text-destructive">{error}</p>}
      <div className="mt-3 flex justify-end gap-2">
        <Button type="button" variant="ghost" size="sm" onClick={onClose}>
          Cancel
        </Button>
        <Button type="submit" size="sm" disabled={busy}>
          {busy ? "Creating..." : "Create group"}
        </Button>
      </div>
    </form>
  )
}

type AddPeopleBoxProps = {
  chatId: string
  chats: ChatSummary[]
  members: GroupMember[]
  onAdded: (members: GroupMember[]) => void
  onClose: () => void
}

// "Add people", for an admin in the side panel. The reply is the new member list.
export function AddPeopleBox({ chatId, chats, members, onAdded, onClose }: AddPeopleBoxProps) {
  const [picked, setPicked] = useState<Picked>({ userIds: [], emails: [] })
  const [error, setError] = useState("")
  const [busy, setBusy] = useState(false)
  const count = picked.userIds.length + picked.emails.length

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    if (count === 0) return setError("Pick at least one person.")

    setBusy(true)
    setError("")
    try {
      const body = { user_ids: picked.userIds, emails: picked.emails }
      onAdded(await api<GroupMember[]>(`/chats/${chatId}/members`, { method: "POST", body }))
    } catch (err) {
      setError(groupError(err))
      setBusy(false)
    }
  }

  return (
    // In the side panel's flow, not a popover: the panel scrolls, and would cut a popover off
    <form
      onSubmit={handleSubmit}
      onKeyDown={(e) => e.key === "Escape" && onClose()}
      noValidate
      className="mt-2 rounded-lg bg-card p-3 ring-1 ring-border"
    >
      <p className="text-name">Add people</p>
      <PeoplePicker people={pickable(chats, members)} picked={picked} onChange={setPicked} />
      {error && <p className="mt-2 text-sm text-destructive">{error}</p>}
      <div className="mt-3 flex justify-end gap-2">
        <Button type="button" variant="ghost" size="sm" onClick={onClose}>
          Cancel
        </Button>
        <Button type="submit" size="sm" disabled={busy}>
          {busy ? "Adding..." : count > 1 ? `Add ${count}` : "Add"}
        </Button>
      </div>
    </form>
  )
}
