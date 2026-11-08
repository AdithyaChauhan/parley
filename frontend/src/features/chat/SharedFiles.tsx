import { useCallback, useEffect, useState } from "react"
import { Download, Folder } from "lucide-react"
import { api } from "@/lib/api"
import { fileUrl, kindText, saveFile, sizeText } from "@/lib/files"
import { useLiveEvents } from "@/lib/live"
import { DocumentIcon, ImageViewer, VoicePlayer } from "./FileContent"
import type { FileData, ServerMessage } from "./types"

type FilePage = { messages: ServerMessage[]; has_more: boolean }

const dataOf = (message: ServerMessage) => message.data as FileData

// One picture in the list. Tapping it opens it large.
function ImageRow({ chatId, data }: { chatId: string; data: FileData }) {
  const [url, setUrl] = useState<string | null>(null)
  const [failed, setFailed] = useState(false)
  return (
    <>
      <button
        type="button"
        aria-label={`Open ${data.name}`}
        onClick={() => fileUrl(chatId, data.file_id).then(setUrl, () => setFailed(true))}
        className="flex min-w-0 flex-1 items-center gap-3 text-left"
      >
        <img src={data.preview ?? undefined} alt="" className="size-11 shrink-0 rounded-lg bg-accent object-cover" />
        <RowText name={data.name} detail={failed ? "Not available" : `${kindText(data)} · ${sizeText(data.size)}`} />
      </button>
      {url && <ImageViewer chatId={chatId} data={data} url={url} onClose={() => setUrl(null)} />}
    </>
  )
}

function RowText({ name, detail }: { name: string; detail: string }) {
  return (
    <span className="min-w-0 flex-1">
      <span className="block truncate font-medium">{name}</span>
      <span className="block text-label">{detail}</span>
    </span>
  )
}

function DocumentRow({ chatId, data }: { chatId: string; data: FileData }) {
  const [failed, setFailed] = useState(false)
  return (
    <>
      <DocumentIcon data={data} />
      <RowText name={data.name} detail={failed ? "Not available" : `${kindText(data)} · ${sizeText(data.size)}`} />
      <button
        type="button"
        aria-label={`Download ${data.name}`}
        onClick={() => saveFile(chatId, data).catch(() => setFailed(true))}
        className="flex size-10 shrink-0 items-center justify-center rounded-lg text-muted-foreground hover:bg-card"
      >
        <Download className="size-5" />
      </button>
    </>
  )
}

// The side panel's list of everything shared in this chat, newest first
export function SharedFiles({ chatId }: { chatId: string }) {
  const [files, setFiles] = useState<ServerMessage[] | null>(null) // null = still loading
  const [hasMore, setHasMore] = useState(false)

  const load = useCallback(
    (before?: number) =>
      api<FilePage>(`/chats/${chatId}/files${before ? `?before=${before}` : ""}`).then((page) => {
        setFiles((current) => [...(before ? (current ?? []) : []), ...page.messages])
        setHasMore(page.has_more)
      }),
    [chatId],
  )

  useEffect(() => {
    load().catch(() => setFiles([]))
  }, [load])

  // A new file in this chat goes on top
  useLiveEvents((event) => {
    if (event.type !== "message.new" || event.data.chat_id !== chatId || event.data.kind !== "file") return
    setFiles((current) =>
      current?.some((file) => file.id === event.data.id) ? current : [event.data, ...(current ?? [])],
    )
  })

  if (files === null) return null

  if (files.length === 0) {
    return (
      <div className="flex flex-col items-center gap-3 rounded-lg bg-row-selected px-4 py-10 text-center">
        <span className="flex size-12 items-center justify-center rounded-lg bg-accent text-primary">
          <Folder className="size-5" />
        </span>
        <p className="text-muted-foreground">No files yet</p>
      </div>
    )
  }

  return (
    <section className="pb-4">
      <h3 className="mb-2 text-label">Files</h3>
      <ul className="flex flex-col gap-1">
        {files.map((file) => {
          const data = dataOf(file)
          return (
            <li key={file.id} className="flex min-w-0 items-center gap-3 rounded-lg p-2 hover:bg-row-selected">
              {data.category === "image" && <ImageRow chatId={chatId} data={data} />}
              {data.category === "document" && <DocumentRow chatId={chatId} data={data} />}
              {data.category === "voice" && <VoicePlayer chatId={chatId} data={data} />}
            </li>
          )
        })}
      </ul>
      {hasMore && (
        <button
          type="button"
          onClick={() => load(files.at(-1)?.seq)}
          className="mt-2 w-full rounded-lg py-2 text-sm text-primary hover:bg-row-selected"
        >
          Show more
        </button>
      )}
    </section>
  )
}
