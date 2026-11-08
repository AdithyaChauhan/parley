// Files and voice notes in the browser (D38): what may be sent, getting a
// file's details ready, and talking to the store through short-lived links.
import { api, ApiError } from "@/lib/api"
import type { FileCategory, FileData } from "@/features/chat/types"

export const MAX_FILE_BYTES = 10 * 1024 * 1024 // 10 MB, also checked by the server and the store
export const MAX_VOICE_MS = 2 * 60 * 1000 // 2 minutes

// Browsers disagree on a file's type (Windows calls a zip x-zip-compressed), so
// the extension decides, using the exact names the server allows.
const typesByExtension: Record<string, { type: string; category: FileCategory }> = {
  jpg: { type: "image/jpeg", category: "image" },
  jpeg: { type: "image/jpeg", category: "image" },
  png: { type: "image/png", category: "image" },
  webp: { type: "image/webp", category: "image" },
  gif: { type: "image/gif", category: "image" },
  pdf: { type: "application/pdf", category: "document" },
  txt: { type: "text/plain", category: "document" },
  docx: { type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document", category: "document" },
  xlsx: { type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", category: "document" },
  pptx: { type: "application/vnd.openxmlformats-officedocument.presentationml.presentation", category: "document" },
  zip: { type: "application/zip", category: "document" },
}

// For the file picker
export const ACCEPTED_FILES = Object.keys(typesByExtension)
  .map((extension) => `.${extension}`)
  .join(",")

function extensionOf(name: string) {
  return name.split(".").pop()?.toLowerCase() ?? ""
}

// A file ready to go: everything the outbox needs
export type PreparedFile = {
  blob: Blob
  name: string
  type: string
  category: FileCategory
  width?: number
  height?: number
  preview?: string
  durationMs?: number
}

// The picture's size, and a tiny copy to show until the real one arrives
async function imageDetails(file: File) {
  const bitmap = await createImageBitmap(file)
  const scale = 40 / Math.max(bitmap.width, bitmap.height, 40)
  const canvas = document.createElement("canvas")
  canvas.width = Math.max(1, Math.round(bitmap.width * scale))
  canvas.height = Math.max(1, Math.round(bitmap.height * scale))
  const context = canvas.getContext("2d")
  if (context) {
    context.fillStyle = "#fff" // a JPEG has no see-through parts
    context.fillRect(0, 0, canvas.width, canvas.height)
    context.drawImage(bitmap, 0, 0, canvas.width, canvas.height)
  }
  const details = { width: bitmap.width, height: bitmap.height, preview: canvas.toDataURL("image/jpeg", 0.5) }
  bitmap.close()
  return details
}

// Checks one picked or dropped file. Returns it ready to go, or the reason it can't be sent.
export async function prepareFile(file: File): Promise<PreparedFile | string> {
  const known = typesByExtension[extensionOf(file.name)]
  if (!known) return `${file.name} isn't a type of file Parley can send`
  if (file.size > MAX_FILE_BYTES) return `${file.name} is over 10 MB`
  if (file.size === 0) return `${file.name} is empty`
  const prepared: PreparedFile = { blob: file, name: file.name, type: known.type, category: known.category }
  if (known.category !== "image") return prepared
  try {
    return { ...prepared, ...(await imageDetails(file)) }
  } catch {
    return `${file.name} couldn't be opened as a picture`
  }
}

// Uploads straight to the store, with progress and a way to cancel (D38).
// XMLHttpRequest, because fetch can't report upload progress.
export function putFile(url: string, type: string, blob: Blob, onProgress: (done: number) => void) {
  const request = new XMLHttpRequest()
  const done = new Promise<void>((resolve, reject) => {
    request.open("PUT", url)
    request.setRequestHeader("Content-Type", type)
    request.upload.onprogress = (event) => {
      if (event.lengthComputable) onProgress(event.loaded / event.total)
    }
    request.onload = () => (request.status < 300 ? resolve() : reject(new ApiError(request.status, null)))
    request.onerror = () => reject(new ApiError(0, null))
    request.onabort = () => reject(new ApiError(0, null))
    request.send(blob)
  })
  return { done, abort: () => request.abort() }
}

// --- Download links: asked for once, then reused until they're nearly out of date ---

const links = new Map<string, { url: Promise<string>; until: number }>()

export function fileUrl(chatId: string, fileId: string, download = false): Promise<string> {
  const key = `${fileId}:${download}`
  const known = links.get(key)
  if (known && known.until > Date.now()) return known.url
  const url = api<{ url: string; expires_in: number }>(
    `/chats/${chatId}/files/${fileId}/url${download ? "?download=true" : ""}`,
  ).then((reply) => {
    // A minute early, so a link is never handed out just as it runs out
    links.set(key, { url, until: Date.now() + (reply.expires_in - 60) * 1000 })
    return reply.url
  })
  url.catch(() => links.delete(key)) // not remembered: the next look asks again
  links.set(key, { url, until: Date.now() + 30_000 })
  return url
}

// Saves a file to the device
export async function saveFile(chatId: string, data: FileData) {
  const link = document.createElement("a")
  link.href = await fileUrl(chatId, data.file_id, true)
  link.download = data.name
  link.click()
}

// --- My own just-sent pictures stay on screen from memory, instead of downloading them again ---

const recent = new Map<string, string>() // file id -> a blob: address (pictures and voice notes)
const MAX_RECENT = 20

export function rememberLocal(fileId: string, localUrl: string) {
  recent.set(fileId, localUrl)
  if (recent.size > MAX_RECENT) {
    const [oldest, url] = recent.entries().next().value as [string, string]
    recent.delete(oldest)
    URL.revokeObjectURL(url)
  }
}

export function localUrlOf(fileId: string) {
  return recent.get(fileId)
}

// --- Words for the screen ---

export function sizeText(bytes: number) {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

export function clockText(ms: number) {
  const seconds = Math.round(ms / 1000)
  return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, "0")}`
}

// "PDF", "DOCX" ...: the card's label
export function kindText(data: FileData) {
  return extensionOf(data.name).toUpperCase() || "FILE"
}
