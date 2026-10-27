import { useState, type FormEvent } from "react"
import { SendHorizontal } from "lucide-react"
import { Button } from "@/components/ui/button"

type MessageBoxProps = {
  onSend: (text: string) => void
  onTyping: () => void // called on every key; live.ts sends at most one "typing" every 3 s
}

// The white box at the bottom: type a message, press Enter or the teal button
export function MessageBox({ onSend, onTyping }: MessageBoxProps) {
  const [text, setText] = useState("")

  function handleSubmit(e: FormEvent) {
    e.preventDefault() // stop the browser reloading the page
    const trimmed = text.trim()
    if (!trimmed) return
    onSend(trimmed)
    setText("")
  }

  return (
    <form
      onSubmit={handleSubmit}
      // Tighter on a phone, so the typing space keeps its room
      className="flex h-16 items-center gap-2 rounded-panel bg-card pr-2 pl-4 shadow-sm shadow-foreground/5 md:gap-3 md:pl-6"
    >
      <input
        value={text}
        onChange={(e) => {
          setText(e.target.value)
          if (e.target.value.trim()) onTyping() // deleting everything isn't typing
        }}
        placeholder="Write your message..."
        aria-label="Message"
        className="min-w-0 flex-1 bg-transparent text-ellipsis outline-none placeholder:text-muted-foreground"
      />
      <Button type="submit" aria-label="Send" className="ml-1 size-12 shrink-0 rounded-lg md:ml-2">
        <SendHorizontal className="size-5" />
      </Button>
    </form>
  )
}
