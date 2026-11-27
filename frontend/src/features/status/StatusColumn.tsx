import { useRef, type ReactNode } from "react"
import { ImagePlus, Type } from "lucide-react"
import { Avatar } from "@/components/Avatar"
import { cn } from "@/lib/utils"
import { listTime } from "@/features/chat/time"
import { tintFor } from "@/features/chat/types"
import { SectionTabs, type Section } from "./SectionTabs"
import type { PersonStatuses, StatusFeed } from "./types"

type StatusColumnProps = {
  feed: StatusFeed | null // null = still loading
  myId: string
  myName: string
  phoneVisible: boolean
  onSection: (section: Section) => void
  onOpen: (userId: string) => void // watch this person's statuses (my own id: mine)
  onWriteText: () => void
  onPickPhoto: (file: File) => void
  problem: string | null // why a picked photo can't be used
}

// An avatar inside a ring: teal while there's something new, grey once it's all seen
export function StatusRing({
  name,
  id,
  unseen,
  size = "md",
}: {
  name: string
  id: string
  unseen: boolean
  size?: "md" | "lg"
}) {
  return (
    <span className={cn("shrink-0 rounded-full p-0.5 ring-2", unseen ? "ring-primary" : "ring-rail-icon")}>
      <Avatar name={name} tint={tintFor(id)} size={size} />
    </span>
  )
}

function PersonRow({ person, onOpen }: { person: PersonStatuses; onOpen: () => void }) {
  const newest = person.statuses[person.statuses.length - 1]
  return (
    <button
      type="button"
      onClick={onOpen}
      className="flex w-full items-center gap-3 rounded-lg px-3 py-3 text-left hover:bg-row-selected"
    >
      <StatusRing name={person.name} id={person.user_id} unseen={!person.all_viewed} />
      <span className="min-w-0 flex-1">
        <span className="block truncate font-medium">{person.name}</span>
        <span className="block text-sm text-muted-foreground">{listTime(newest.posted_at)}</span>
      </span>
    </button>
  )
}

function Heading({ children }: { children: ReactNode }) {
  return <h2 className="mt-4 mb-1 px-3 text-sm text-muted-foreground">{children}</h2>
}

// The left column in the Status section (D41): my status with its two ways to
// post, then my people's statuses, new ones first, then the ones I've seen.
export function StatusColumn({
  feed,
  myId,
  myName,
  phoneVisible,
  onSection,
  onOpen,
  onWriteText,
  onPickPhoto,
  problem,
}: StatusColumnProps) {
  const picker = useRef<HTMLInputElement>(null)
  const mine = feed?.mine ?? []
  const recent = feed?.people.filter((p) => !p.all_viewed) ?? []
  const viewed = feed?.people.filter((p) => p.all_viewed) ?? []
  const newest = mine[mine.length - 1]

  return (
    <section
      className={cn(
        "min-h-0 flex-1 flex-col px-4 md:w-70 md:flex-none lg:w-85",
        phoneVisible ? "flex" : "hidden md:flex",
      )}
    >
      <div className="flex shrink-0 flex-col pt-6 pb-3">
        <h1 className="px-1 text-header font-medium">Status</h1>
        <SectionTabs section="status" onSection={onSection} unseen={false} className="mt-4" />
      </div>

      <div className="-mx-1 min-h-0 flex-1 overflow-y-auto overscroll-contain px-1 pb-4 scrollbar-thin">
        {/* My status: open it to watch mine and see who viewed them, or post a new one */}
        <div className="flex items-center gap-2 rounded-lg bg-search px-3 py-3">
          <button
            type="button"
            onClick={() => (mine.length ? onOpen(myId) : onWriteText())}
            className="flex min-w-0 flex-1 items-center gap-3 text-left"
          >
            {mine.length ? <StatusRing name={myName} id={myId} unseen={false} /> : <Avatar name={myName} tint="teal" />}
            <span className="min-w-0">
              <span className="block truncate font-medium">My status</span>
              <span className="block truncate text-sm text-muted-foreground">
                {newest
                  ? `${mine.length} ${mine.length === 1 ? "update" : "updates"} · ${listTime(newest.posted_at)}`
                  : "Add a text or photo"}
              </span>
            </span>
          </button>
          <button
            type="button"
            onClick={onWriteText}
            aria-label="New text status"
            className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-accent text-primary"
          >
            <Type className="size-4" />
          </button>
          <button
            type="button"
            onClick={() => picker.current?.click()}
            aria-label="New photo status"
            className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-accent text-primary"
          >
            <ImagePlus className="size-4" />
          </button>
          <input
            ref={picker}
            type="file"
            accept=".jpg,.jpeg,.png,.webp,.gif"
            className="hidden"
            onChange={(e) => {
              const file = e.target.files?.[0]
              e.target.value = "" // the same photo can be picked again
              if (file) onPickPhoto(file)
            }}
          />
        </div>

        {problem && <p className="px-3 pt-2 text-sm text-destructive">{problem}</p>}
        {!feed && <p className="px-3 py-6 text-sm text-muted-foreground">Loading statuses...</p>}
        {recent.length > 0 && <Heading>Recent updates</Heading>}
        {recent.map((person) => (
          <PersonRow key={person.user_id} person={person} onOpen={() => onOpen(person.user_id)} />
        ))}
        {viewed.length > 0 && <Heading>Viewed updates</Heading>}
        {viewed.map((person) => (
          <PersonRow key={person.user_id} person={person} onOpen={() => onOpen(person.user_id)} />
        ))}
        {feed && feed.people.length === 0 && (
          <p className="px-3 py-6 text-sm text-muted-foreground">No updates from your chats right now.</p>
        )}
        <p className="px-3 pt-4 text-label text-muted-foreground">
          Statuses disappear after 24 hours. Everyone you have a 1:1 chat with can see yours.
        </p>
      </div>
    </section>
  )
}
