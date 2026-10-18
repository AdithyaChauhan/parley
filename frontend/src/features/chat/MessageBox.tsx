import { useState, type FormEvent } from "react"
import { Paperclip, SendHorizontal, Smile } from "lucide-react"
import { Button } from "@/components/ui/button"

// The white box at the bottom: type a message, press Enter or the teal button
export function MessageBox({ onSend }: { onSend: (text: string) => void }) {
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
      className="flex h-16 items-center gap-3 rounded-panel bg-card pr-2 pl-6 shadow-sm shadow-foreground/5"
    >
      <input
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder="Write your message..."
        aria-label="Message"
        className="min-w-0 flex-1 bg-transparent outline-none placeholder:text-muted-foreground"
      />
      <button type="button" aria-label="Emoji" className="text-rail-icon hover:text-muted-foreground">
        <Smile className="size-5" />
      </button>
      <button type="button" aria-label="Attach a file" className="text-rail-icon hover:text-muted-foreground">
        <Paperclip className="size-5" />
      </button>
      <Button type="submit" aria-label="Send" className="ml-2 size-12 rounded-lg">
        <SendHorizontal className="size-5" />
      </Button>
    </form>
  )
}
