import { useRef, useState } from "react"
import { api, ApiError, isBusy, isUnreachable } from "@/lib/api"
import { putFile, rememberLocal, type PreparedFile } from "@/lib/files"
import { announce, useLiveEvents } from "@/lib/live"
import { NOT_CHANGED, type FileData, type Message, type ServerMessage } from "./types"

const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms))

// A file on its way (D38): the bytes, and how far it got
type FileJob = { blob: Blob; fileId?: string; abort?: () => void; cancelled: boolean }

// My messages that aren't saved yet, per chat, in the order I wrote them (D21).
// Every send goes through here, one at a time per chat, so a new message never
// overtakes an older one. It lives in ChatScreen, above the Conversation, so it
// keeps sending after you switch chats, and a "Not sent" message is still there when you come back.
//   - No answer (offline, or the server is down): the message waits, with
//     everything after it, until the line is back. Then they go out in order.
//   - Too many sends (429, D24) or a busy server (503, D34): the same "waiting",
//     but it goes again by itself after the server's Retry-After, still in order.
//   - A real refusal (like 422): "Not sent, tap to retry", and the next one goes on.
// Each message keeps its clientMsgId for every try, so if one did get through
// before the drop, the server hands back that first copy instead of a double (D18).
export function useOutbox(myId: string) {
  const [unsent, setUnsent] = useState<Record<string, Message[]>>({})
  // The same lists, readable at once inside a running send (state only updates on the next render)
  const lists = useRef<Record<string, Message[]>>({})
  // Chats whose queue is being sent right now
  const busy = useRef(new Set<string>())
  // What a file message needs while it's on its way, by clientMsgId
  const files = useRef(new Map<string, FileJob>())

  function update(chatId: string, change: (list: Message[]) => Message[]) {
    lists.current = { ...lists.current, [chatId]: change(lists.current[chatId] ?? []) }
    setUnsent(lists.current)
  }

  // Sends this chat's queue, oldest first, one at a time, until it's empty or the line is down
  async function sendQueue(chatId: string) {
    if (busy.current.has(chatId)) return // already going: it will reach the new ones too
    busy.current.add(chatId)
    try {
      while (true) {
        // Files have their own queue, so a big upload doesn't hold up a text
        const next = lists.current[chatId]?.find((m) => m.kind !== "file" && (m.status === "sending" || m.status === "waiting"))
        if (!next) return
        const mark = (status: Message["status"]) =>
          update(chatId, (list) => list.map((m) => (m.clientMsgId === next.clientMsgId ? { ...m, status } : m)))

        mark("sending")
        try {
          const reply = await api<ServerMessage>(`/chats/${chatId}/messages`, {
            method: "POST",
            body: { client_msg_id: next.clientMsgId, body: next.body },
          })
          update(chatId, (list) => list.filter((m) => m.clientMsgId !== next.clientMsgId))
          // The reply is a saved message, like a pushed one, so it goes in the same way:
          // the chat list moves, and a skipped number starts a catch-up (D21)
          announce({ type: "message.new", data: reply })
        } catch (error) {
          const waitAll = () =>
            update(chatId, (list) =>
              list.map((m) => (m.status === "failed" || m.kind === "file" ? m : { ...m, status: "waiting" })),
            )
          if ((error instanceof ApiError && error.status === 429) || isBusy(error)) {
            // Slow down: this one and everything after it wait, then the loop
            // picks up the oldest again. The queue stays busy meanwhile, so nothing overtakes it.
            waitAll()
            await sleep((error.retryAfter ?? 1) * 1000)
            continue
          }
          if (isUnreachable(error)) {
            // Offline: this one and everything after it wait for the line
            waitAll()
            return
          }
          mark("failed")
        }
      }
    } finally {
      busy.current.delete(chatId)
    }
  }

  // One file at a time per chat, in the order they were added
  async function sendFiles(chatId: string) {
    const queue = `files:${chatId}`
    if (busy.current.has(queue)) return
    busy.current.add(queue)
    try {
      while (true) {
        const next = lists.current[chatId]?.find((m) => m.kind === "file" && (m.status === "sending" || m.status === "waiting"))
        if (!next) return
        if (!(await sendOneFile(chatId, next))) return
      }
    } finally {
      busy.current.delete(queue)
    }
  }

  // Upload, then save the message (D9). Returns false if the queue should stop for now.
  async function sendOneFile(chatId: string, message: Message): Promise<boolean> {
    const job = files.current.get(message.clientMsgId)
    if (!job) return true
    const data = message.data as FileData
    const change = (patch: Partial<Message>) =>
      update(chatId, (list) => list.map((m) => (m.clientMsgId === message.clientMsgId ? { ...m, ...patch } : m)))
    const finish = () => {
      files.current.delete(message.clientMsgId)
      update(chatId, (list) => list.filter((m) => m.clientMsgId !== message.clientMsgId))
    }

    change({ status: "sending" })
    try {
      if (!job.fileId) {
        change({ progress: 0 })
        const grant = await api<{ file_id: string; url: string; content_type: string }>(`/chats/${chatId}/uploads`, {
          method: "POST",
          body: { name: data.name, type: data.type, size: data.size },
        })
        if (job.cancelled) return true
        let shown = 0
        const put = putFile(grant.url, grant.content_type, job.blob, (done) => {
          // Only when the number on screen changes
          if (Math.round(done * 100) !== shown) {
            shown = Math.round(done * 100)
            change({ progress: done })
          }
        })
        job.abort = put.abort
        await put.done
        job.fileId = grant.file_id
        job.abort = undefined
        change({ progress: 1 })
        if (message.localUrl) rememberLocal(grant.file_id, message.localUrl)
      }

      const reply = await api<ServerMessage>(`/chats/${chatId}/files`, {
        method: "POST",
        body: {
          client_msg_id: message.clientMsgId,
          file_id: job.fileId,
          width: data.width ?? undefined,
          height: data.height ?? undefined,
          preview: data.preview ?? undefined,
          duration_ms: data.duration_ms ?? undefined,
        },
      })
      finish()
      announce({ type: "message.new", data: reply })
      return true
    } catch (error) {
      if (job.cancelled) return true
      if ((error instanceof ApiError && error.status === 429) || isBusy(error)) {
        change({ status: "waiting" })
        await sleep((error.retryAfter ?? 1) * 1000)
        return true
      }
      // Really offline: waits for the line, and starts again from the upload if it didn't finish
      if (error instanceof ApiError && error.status === 0 && !navigator.onLine) {
        change({ status: "waiting" })
        return false
      }
      if (isUnreachable(error) && job.fileId) {
        change({ status: "waiting" })
        return false
      }
      change({ status: "failed" })
      return true
    }
  }

  // Shows the file at once, then uploads it in its turn
  function sendFile(chatId: string, file: PreparedFile) {
    const clientMsgId = crypto.randomUUID()
    const data: FileData = {
      file_id: "",
      name: file.name,
      type: file.type,
      size: file.blob.size,
      category: file.category,
      width: file.width,
      height: file.height,
      preview: file.preview,
      duration_ms: file.durationMs,
    }
    files.current.set(clientMsgId, { blob: file.blob, cancelled: false })
    const message: Message = {
      id: null,
      clientMsgId,
      seq: null,
      senderId: myId,
      senderName: "",
      body: "",
      createdAt: new Date().toISOString(),
      status: "sending",
      kind: "file",
      data,
      ...NOT_CHANGED,
      progress: 0,
      // Pictures and voice notes show or play from this device while they upload
      localUrl: file.category === "document" ? undefined : URL.createObjectURL(file.blob),
    }
    update(chatId, (list) => [...list, message])
    sendFiles(chatId)
  }

  // Stops a file that's on its way, and takes it off the screen
  function cancel(chatId: string, message: Message) {
    const job = files.current.get(message.clientMsgId)
    if (job) {
      job.cancelled = true
      job.abort?.()
      files.current.delete(message.clientMsgId)
    }
    if (message.localUrl) URL.revokeObjectURL(message.localUrl)
    update(chatId, (list) => list.filter((m) => m.clientMsgId !== message.clientMsgId))
  }

  // Shows the message at once, then sends it in its turn
  function send(chatId: string, body: string) {
    const message: Message = {
      id: null,
      clientMsgId: crypto.randomUUID(), // a fresh ID for each new message (D9)
      seq: null,
      senderId: myId,
      senderName: "", // mine: shown as "You"
      body,
      createdAt: new Date().toISOString(),
      status: "sending",
      kind: "text",
      data: null,
      ...NOT_CHANGED,
    }
    update(chatId, (list) => [...list, message])
    sendQueue(chatId)
  }

  // "Not sent, tap to retry": back in the queue, with the SAME clientMsgId
  function retry(chatId: string, message: Message) {
    update(chatId, (list) => list.map((m) => (m.clientMsgId === message.clientMsgId ? { ...m, status: "sending" } : m)))
    if (message.kind === "file") sendFiles(chatId)
    else sendQueue(chatId)
  }

  // On the line again: every chat's waiting messages go out, in order (D21)
  useLiveEvents((event) => {
    if (event.type !== "hello") return
    for (const chatId of Object.keys(lists.current)) {
      sendQueue(chatId)
      sendFiles(chatId)
    }
  })

  return { unsent, send, retry, sendFile, cancel }
}
