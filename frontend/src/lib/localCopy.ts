// This device's own copy of the messages it has seen, in IndexedDB, so search
// runs here and the server never searches text (D12, D40). One database per
// user, removed on log-out.
//
// The copy only ever helps. If the browser refuses (no space, private mode),
// chat carries on and search just finds less, so nothing here throws.
import { api, ApiError, isBusy } from "@/lib/api"
import { isEvent, type ChatSummary, type FileData, type MessagePage, type ServerMessage } from "@/features/chat/types"

const PREFIX = "parley-copy-"
// A cap on what's shown; the search itself is quick either way
const MAX_HITS = 100
// Between pages of background fetching, so it never crowds out the chat (D24)
const PAGE_PAUSE_MS = 250

// One message as this device keeps it: only what search needs
export type Kept = {
  id: string
  chatId: string
  seq: number
  senderId: string
  senderName: string
  text: string // the message, or a file's name. Empty once deleted.
  isFile: boolean
  time: number
  stateSeq: number // the higher copy wins, like on screen (D39)
}

// Per chat: how far the copy is known to be up to date
type Mark = {
  chatId: string
  upTo: number // every change numbered up to this has been applied here
  historyBefore?: number // "Load all my history": still to fetch below this. 0 = all done.
}

const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms))

let database: Promise<IDBDatabase | null> | null = null
let owner: string | null = null
// Goes up whenever the copy opens or closes, so a long fetch can tell it should stop
let session = 0

// Someone's listening for changes: results on screen follow edits and deletes
const listeners = new Set<() => void>()

export function onCopyChanged(listener: () => void) {
  listeners.add(listener)
  return () => {
    listeners.delete(listener)
  }
}

function stop() {
  owner = null
  database = null
  session += 1
}

function open(name: string): Promise<IDBDatabase | null> {
  return new Promise((resolve) => {
    try {
      const request = indexedDB.open(name, 1)
      request.onupgradeneeded = () => {
        const messages = request.result.createObjectStore("messages", { keyPath: "id" })
        messages.createIndex("byChat", ["chatId", "seq"])
        messages.createIndex("byTime", "time")
        request.result.createObjectStore("marks", { keyPath: "chatId" })
      }
      request.onerror = () => resolve(null)
      request.onsuccess = () => {
        const db = request.result
        // Logged out in another tab: it's waiting to remove this database. Let
        // go, and write nothing more, or the copy would come back.
        db.onversionchange = () => {
          db.close()
          stop()
        }
        resolve(db)
      }
    } catch {
      resolve(null)
    }
  })
}

// Start of a session. Anyone else's copy goes: on a shared computer, a session
// that simply ran out left one behind.
export function openCopy(userId: string) {
  if (owner === userId || typeof indexedDB === "undefined") return
  owner = userId
  session += 1
  database = open(PREFIX + userId)
  indexedDB
    .databases?.()
    .then((all) => {
      for (const { name } of all) {
        if (name?.startsWith(PREFIX) && name !== PREFIX + userId) indexedDB.deleteDatabase(name)
      }
    })
    .catch(() => {})
}

// Log-out: nothing stays on this device (D40). Other tabs let go through onversionchange.
export function eraseCopy() {
  if (!owner) return
  const name = PREFIX + owner
  const closing = database
  stop()
  closing?.then((db) => db?.close())
  indexedDB.deleteDatabase(name)
}

// One transaction. Resolves with what `work` returned, once it's safely done;
// null if the copy is closed or the browser refused.
async function transaction<T>(
  stores: string[],
  mode: IDBTransactionMode,
  work: (tx: IDBTransaction) => T,
): Promise<T | null> {
  const db = await database
  if (!db) return null
  return new Promise((resolve) => {
    try {
      const tx = db.transaction(stores, mode)
      const result = work(tx)
      tx.oncomplete = () => resolve(result)
      tx.onerror = tx.onabort = () => resolve(null)
    } catch {
      resolve(null) // closed while we were on our way
    }
  })
}

// What's worth keeping from a server message. Group notes and voice notes have
// no words to search. A deleted one stays as an empty row: it finds nothing,
// and its number stops an older copy, still on its way, from bringing it back.
function toKept(message: ServerMessage): Kept | null {
  if (message.kind !== "text" && message.kind !== "file") return null
  const file = message.kind === "file" && !message.deleted ? (message.data as FileData) : null
  if (file?.category === "voice") return null
  return {
    id: message.id,
    chatId: message.chat_id,
    seq: message.seq,
    senderId: message.sender_id,
    senderName: message.sender_name,
    text: message.deleted ? "" : file ? file.name : message.body,
    isFile: file !== null,
    time: Date.parse(message.created_at),
    stateSeq: message.state_seq,
  }
}

// Change one chat's mark inside a running transaction
function patchMark(tx: IDBTransaction, chatId: string, fallbackUpTo: number, change: (mark: Mark) => void) {
  const marks = tx.objectStore("marks")
  const read = marks.get(chatId)
  read.onsuccess = () => {
    const mark: Mark = read.result ?? { chatId, upTo: fallbackUpTo }
    change(mark)
    marks.put(mark)
  }
}

// Saved messages in, or the message an event changed. `live`: a pushed one,
// which moves the mark if it's the very next number.
export async function keep(messages: ServerMessage[], live = false) {
  const rows = messages.flatMap((message) => {
    const source = isEvent(message) ? message.target : message
    const row = source && toKept(source)
    return row ? [row] : []
  })
  if (rows.length === 0 && !live) return

  await transaction(["messages", "marks"], "readwrite", (tx) => {
    const store = tx.objectStore("messages")
    for (const row of rows) {
      const read = store.get(row.id)
      read.onsuccess = () => {
        if (!read.result || row.stateSeq >= read.result.stateSeq) store.put(row)
      }
    }
    if (live && messages[0]) {
      const { chat_id: chatId, seq } = messages[0]
      // No fallback row: a chat with no mark yet gets one from the next syncCopy
      const marks = tx.objectStore("marks")
      const read = marks.get(chatId)
      read.onsuccess = () => {
        const mark: Mark | undefined = read.result
        if (mark && seq === mark.upTo + 1) marks.put({ ...mark, upTo: seq })
      }
    }
  })
  for (const listener of listeners) listener()
}

// A page from the server, waiting out "too many" and "busy" (D24, D34)
async function getPage(path: string) {
  for (let tries = 1; ; tries++) {
    try {
      return await api<MessagePage>(path)
    } catch (error) {
      const slowDown = (error instanceof ApiError && error.status === 429) || isBusy(error)
      if (!slowDown || tries === 5) throw error
      await sleep(((error as ApiError).retryAfter ?? 1) * 1000)
    }
  }
}

async function readMarks() {
  const read = await transaction(["marks"], "readonly", (tx) => tx.objectStore("marks").getAll())
  return read && new Map((read.result as Mark[]).map((mark) => [mark.chatId, mark]))
}

let syncing = false

// Brings the copy up to date with what happened while this device was away:
// an edit or delete in a chat I didn't open must not stay findable here (D40).
// Asks only for chats whose number moved past the mark, so usually nothing.
export async function syncCopy(chats: ChatSummary[]) {
  if (syncing) return
  syncing = true
  const mine = session
  try {
    const marks = await readMarks()
    if (!marks) return
    for (const chat of chats) {
      const mark = marks.get(chat.id)
      if (!mark) {
        // Seen for the first time: nothing held here, so nothing can be out of date
        await transaction(["marks"], "readwrite", (tx) => patchMark(tx, chat.id, chat.last_seq, () => {}))
        continue
      }
      if (mark.upTo >= chat.last_seq) continue

      let after = mark.upTo
      for (let more = true; more; ) {
        const page = await getPage(`/chats/${chat.id}/messages?after=${after}&limit=100`)
        if (session !== mine) return
        await keep(page.messages)
        more = page.has_more
        after = page.messages.at(-1)?.seq ?? after
        if (more) await sleep(PAGE_PAUSE_MS)
      }
      // Up to where the list said at the start, also if I left and the page was empty
      const upTo = Math.max(after, chat.last_seq)
      await transaction(["marks"], "readwrite", (tx) =>
        patchMark(tx, chat.id, upTo, (saved) => {
          saved.upTo = Math.max(saved.upTo, upTo)
        }),
      )
      await sleep(PAGE_PAUSE_MS)
    }
  } catch {
    // Nothing lost: the marks didn't move, so the next re-check tries again
  } finally {
    syncing = false
  }
}

// A chat counts as finished once its pages reached the beginning
function historyDone(chat: ChatSummary, marks: Map<string, Mark>) {
  return chat.last_seq === 0 || marks.get(chat.id)?.historyBefore === 0
}

// How many chats still have older messages to bring here. Null: the copy isn't open.
export async function chatsWithHistoryLeft(chats: ChatSummary[]) {
  const marks = await readMarks()
  return marks && chats.filter((chat) => !historyDone(chat, marks)).length
}

// "Load all my history": every chat's older pages, one page at a time, picking
// up where it stopped. Newest first, so a stop still leaves the useful part.
export async function loadAllHistory(
  chats: ChatSummary[],
  onProgress: (messages: number) => void,
  shouldStop: () => boolean,
): Promise<"done" | "stopped" | "failed"> {
  const mine = session
  const marks = await readMarks()
  if (!marks) return "failed"
  let total = 0
  try {
    for (const chat of chats) {
      if (historyDone(chat, marks)) continue
      let before = marks.get(chat.id)?.historyBefore
      for (;;) {
        if (shouldStop()) return "stopped"
        const query = before ? `&before=${before}` : ""
        const page = await getPage(`/chats/${chat.id}/messages?limit=100${query}`)
        if (session !== mine) return "stopped"
        await keep(page.messages)
        // Newest first, so the last one on the page is the lowest number
        const next = page.has_more ? (page.messages.at(-1)?.seq ?? 0) : 0
        before = next
        await transaction(["marks"], "readwrite", (tx) =>
          patchMark(tx, chat.id, chat.last_seq, (saved) => {
            saved.historyBefore = next
          }),
        )
        total += page.messages.length
        onProgress(total)
        await sleep(PAGE_PAUSE_MS)
        if (next === 0) break
      }
    }
    return "done"
  } catch {
    return "failed"
  }
}

// Case doesn't matter, and whatever you type is taken literally
export function matcher(query: string) {
  return new RegExp(query.trim().replace(/[.*+?^${}()|[\]\\]/g, "\\$&"), "iu")
}

// Matches, newest first: in one chat, or everywhere. `more` means some were cut off.
export async function searchCopy(query: string, chatId?: string) {
  const pattern = matcher(query)
  const read = await transaction(["messages"], "readonly", (tx) => {
    const store = tx.objectStore("messages")
    return chatId
      ? store.index("byChat").getAll(IDBKeyRange.bound([chatId, 0], [chatId, Infinity]))
      : store.index("byTime").getAll()
  })
  const rows = (read?.result ?? []) as Kept[]
  const hits: Kept[] = []
  for (let i = rows.length - 1; i >= 0; i--) {
    if (!pattern.test(rows[i].text)) continue
    if (hits.length === MAX_HITS) return { hits, more: true }
    hits.push(rows[i])
  }
  return { hits, more: false }
}
