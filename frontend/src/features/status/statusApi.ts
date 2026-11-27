// Talking to /api/status (D41). Posting isn't queued like messages: a failed
// post shows its error, and trying again sends the same id, so it's never saved twice.
import { api } from "@/lib/api"
import { putFile, type PreparedFile } from "@/lib/files"
import type { StatusItem, Viewer } from "./types"

export function postText(id: string, body: string, color: number) {
  return api<StatusItem>("/status", {
    method: "POST",
    body: { id, kind: "text", body, color },
  })
}

// Uploads the photo straight to the store, then posts it (D38's way)
export async function postPhoto(id: string, file: PreparedFile, caption: string, onProgress: (done: number) => void) {
  const upload = await api<{ url: string; content_type: string }>("/status/uploads", {
    method: "POST",
    body: { id, type: file.type, size: file.blob.size },
  })
  await putFile(upload.url, upload.content_type, file.blob, onProgress).done
  return api<StatusItem>("/status", {
    method: "POST",
    body: {
      id,
      kind: "image",
      body: caption,
      width: file.width,
      height: file.height,
      preview: file.preview,
    },
  })
}

// "I saw it": counted once on the server, so a repeat does no harm
export function markViewed(id: string) {
  return api<void>(`/status/${id}/view`, { method: "POST" }).catch(() => {})
}

export function viewersOf(id: string) {
  return api<Viewer[]>(`/status/${id}/views`)
}

export function deleteStatus(id: string) {
  return api<void>(`/status/${id}`, { method: "DELETE" })
}

// Photo links, asked for once and reused until they're nearly out of date
const links = new Map<string, { url: Promise<string>; until: number }>()

export function photoUrl(id: string): Promise<string> {
  const known = links.get(id)
  if (known && known.until > Date.now()) return known.url
  const url = api<{ url: string; expires_in: number }>(`/status/${id}/url`).then((reply) => {
    links.set(id, { url, until: Date.now() + (reply.expires_in - 60) * 1000 })
    return reply.url
  })
  url.catch(() => links.delete(id))
  links.set(id, { url, until: Date.now() + 30_000 })
  return url
}
