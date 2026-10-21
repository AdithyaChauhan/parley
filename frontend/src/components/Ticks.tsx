import { Check, CheckCheck, Clock } from "lucide-react"
import type { Tick } from "@/features/chat/types"

// Clock = sending, one grey tick = sent, two grey = delivered, two teal = read (look.md)
export function Ticks({ status }: { status: Tick }) {
  if (status === "sending") {
    return <Clock className="size-3 text-tick" aria-label="Sending" />
  }
  if (status === "sent") {
    return <Check className="size-3.5 text-tick" aria-label="Sent" />
  }
  if (status === "delivered") {
    return <CheckCheck className="size-3.5 text-tick" aria-label="Delivered" />
  }
  return <CheckCheck className="size-3.5 text-primary" aria-label="Read" />
}
