import { useState, type FormEvent } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { checkEmail } from "@/features/auth/validate"
import { api, ApiError, isUnreachable } from "@/lib/api"
import type { ChatSummary } from "./types"

function startChatError(error: unknown) {
  if (error instanceof ApiError && error.status === 404) return "No Parley account with that email."
  if (error instanceof ApiError && error.status === 400) return "That's you."
  if (error instanceof ApiError && error.status === 429) return "Slow down a moment."
  if (isUnreachable(error)) return "Can't reach Parley."
  return "Something went wrong. Try again."
}

type NewChatBoxProps = {
  onStarted: (chat: ChatSummary) => void
  onClose: () => void
}

// The small box under "+": type an email, start a direct chat.
// The reply is a chat-list row, so it can go straight into the list.
export function NewChatBox({ onStarted, onClose }: NewChatBoxProps) {
  const [email, setEmail] = useState("")
  const [error, setError] = useState("")
  const [busy, setBusy] = useState(false)

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    const problem = checkEmail(email) // catches "ben@" before the server sends a 422
    if (problem) {
      setError(problem)
      return
    }

    setBusy(true)
    setError("")
    try {
      onStarted(await api<ChatSummary>("/chats/direct", { method: "POST", body: { email: email.trim() } }))
    } catch (err) {
      setError(startChatError(err))
      setBusy(false)
    }
  }

  return (
    <form
      onSubmit={handleSubmit}
      onKeyDown={(e) => e.key === "Escape" && onClose()}
      noValidate
      className="absolute top-full right-0 z-20 mt-1 w-72 max-w-[calc(100vw-2rem)] rounded-lg bg-card p-3 shadow-lg ring-1 shadow-foreground/10 ring-border"
    >
      <label htmlFor="new-chat-email" className="text-label">
        Start a chat by email
      </label>
      <Input
        id="new-chat-email"
        type="email"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        placeholder="name@example.com"
        aria-invalid={error !== ""}
        autoFocus
        className="mt-2"
      />
      {error && <p className="mt-1.5 text-sm text-destructive">{error}</p>}
      <div className="mt-3 flex justify-end gap-2">
        <Button type="button" variant="ghost" size="sm" onClick={onClose}>
          Cancel
        </Button>
        <Button type="submit" size="sm" disabled={busy}>
          {busy ? "Starting..." : "Start chat"}
        </Button>
      </div>
    </form>
  )
}
