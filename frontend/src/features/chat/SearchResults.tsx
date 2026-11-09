import { ArrowLeft, FileText } from "lucide-react"
import { Avatar } from "@/components/Avatar"
import { matcher, type Kept } from "@/lib/localCopy"
import { listTime } from "./time"
import { tintFor, type ChatSummary, type Tint } from "./types"
import { useSearch, type HistoryLoad } from "./useSearch"

// How many letters of what comes before the match stay visible
const LEAD_IN = 10

// One line of the message, starting close enough to the match that it shows
function snippet(text: string, query: string) {
  const line = text.replace(/\s+/g, " ")
  const at = line.search(matcher(query))
  if (at <= LEAD_IN) return line
  // From a whole word, when there's one nearby
  const space = line.indexOf(" ", at - LEAD_IN)
  return `…${line.slice(space === -1 || space >= at ? at - LEAD_IN : space + 1)}`
}

// The text with every match marked (D40)
function Highlighted({ text, query }: { text: string; query: string }) {
  const parts = snippet(text, query).split(new RegExp(`(${matcher(query).source})`, "iu"))
  return parts.map((part, i) =>
    // split with a group: the matches are at the odd places
    i % 2 === 1 ? (
      <mark key={i} className="rounded-xs bg-accent text-primary">
        {part}
      </mark>
    ) : (
      part
    ),
  )
}

// The honest note, and the optional button that fetches the rest (D40)
function SearchNote({ history }: { history: HistoryLoad }) {
  const link = "text-primary hover:underline"
  return (
    <div className="px-4 pb-2 text-label text-muted-foreground">
      <p>Only searches messages this device has loaded.</p>
      {history.phase === "idle" && (
        <button type="button" onClick={history.start} className={link}>
          Load all my history
        </button>
      )}
      {history.phase === "failed" && (
        <p>
          Couldn't load all of it.{" "}
          <button type="button" onClick={history.start} className={link}>
            Try again
          </button>
        </p>
      )}
      {history.phase === "loading" && (
        <p>
          Loading older messages... {history.count} so far.{" "}
          <button type="button" onClick={history.stop} className={link}>
            Stop
          </button>
        </p>
      )}
      {history.phase === "done" && <p>All your history is on this device.</p>}
    </div>
  )
}

function HitRow({
  hit,
  query,
  title,
  avatarName,
  avatarTint,
  sender,
  onOpen,
}: {
  hit: Kept
  query: string
  title: string
  avatarName: string
  avatarTint: Tint
  sender: string | null // Left out when the title already says who
  onOpen: () => void
}) {
  return (
    <button
      type="button"
      onClick={onOpen}
      className="flex w-full items-center gap-3 rounded-lg px-4 py-3 text-left hover:bg-row-selected/60"
    >
      <Avatar name={avatarName} tint={avatarTint} />
      <div className="min-w-0 flex-1">
        <div className="flex items-baseline justify-between gap-2">
          <span className="truncate text-name leading-tight">{title}</span>
          <span className="shrink-0 text-label text-muted-foreground">{listTime(new Date(hit.time).toISOString())}</span>
        </div>
        <p className="mt-1 flex items-center gap-1 text-sm text-muted-foreground">
          {hit.isFile && <FileText className="size-3.5 shrink-0" />}
          <span className="truncate">
            {sender && `${sender}: `}
            <Highlighted text={hit.text} query={query} />
          </span>
        </p>
      </div>
    </button>
  )
}

const nothing = <p className="px-4 py-6 text-sm text-muted-foreground">No messages found</p>
const cutOff = <p className="px-4 py-3 text-label text-muted-foreground">Showing the newest 100. Type more to narrow it down.</p>

// Under the chat list's search box: messages from every chat
export function MessageResults({
  query,
  chats,
  myId,
  history,
  onOpen,
}: {
  query: string
  chats: ChatSummary[]
  myId: string
  history: HistoryLoad
  onOpen: (hit: Kept) => void
}) {
  const found = useSearch(query)
  const byId = new Map(chats.map((chat) => [chat.id, chat]))
  const hits = found?.hits.filter((hit) => byId.has(hit.chatId)) ?? []
  return (
    <div className="mt-3">
      <h2 className="px-4 pb-1">Messages</h2>
      <SearchNote history={history} />
      {found && hits.length === 0 && nothing}
      {found &&
        hits.map((hit) => {
          const chat = byId.get(hit.chatId)!
          return (
            <HitRow
              key={hit.id}
              hit={hit}
              query={found.query}
              title={chat.name}
              avatarName={chat.name}
              avatarTint={tintFor(chat.id)}
              sender={hit.senderId === myId ? "You" : hit.senderName}
              onOpen={() => onOpen(hit)}
            />
          )
        })}
      {found?.more && cutOff}
    </div>
  )
}

// Inside a chat: the box takes over the header, and the results the whole panel
export function ChatSearch({
  chat,
  myId,
  query,
  onQuery,
  history,
  onOpen,
  onClose,
}: {
  chat: ChatSummary
  myId: string
  query: string
  onQuery: (query: string) => void
  history: HistoryLoad
  onOpen: (hit: Kept) => void
  onClose: () => void
}) {
  const found = useSearch(query, chat.id)
  return (
    <div
      onKeyDown={(e) => e.key === "Escape" && onClose()}
      className="absolute inset-0 z-20 flex flex-col bg-conversation md:rounded-panel"
    >
      <header className="flex h-16 shrink-0 items-center gap-3 border-b px-4 md:px-6">
        <button
          type="button"
          onClick={onClose}
          aria-label="Close search"
          className="flex size-10 shrink-0 items-center justify-center rounded-lg bg-card text-muted-foreground"
        >
          <ArrowLeft className="size-4" />
        </button>
        <input
          autoFocus
          value={query}
          onChange={(e) => onQuery(e.target.value)}
          placeholder={`Search in ${chat.name}`}
          // 16px on a phone: an iPhone zooms the whole page when you tap a smaller box
          className="h-10 min-w-0 flex-1 rounded-lg bg-card px-4 text-base outline-none placeholder:text-muted-foreground md:text-body"
        />
      </header>
      <div className="min-h-0 flex-1 overflow-y-auto overscroll-contain py-3 scrollbar-thin md:px-2">
        {query.trim() && <SearchNote history={history} />}
        {found && found.hits.length === 0 && nothing}
        {found &&
          found.hits.map((hit) => {
            const name = hit.senderId === myId ? "You" : hit.senderName
            return (
              <HitRow
                key={hit.id}
                hit={hit}
                query={found.query}
                title={name}
                avatarName={name}
                avatarTint={tintFor(chat.kind === "group" ? hit.senderId : chat.id)}
                sender={null}
                onOpen={() => onOpen(hit)}
              />
            )
          })}
        {found?.more && cutOff}
      </div>
    </div>
  )
}
