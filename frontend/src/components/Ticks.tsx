import { Check, CheckCheck } from "lucide-react"
import type { Tick } from "@/data/fake"

// One grey tick = sent, two grey = delivered, two teal = read (look.md)
export function Ticks({ status }: { status: Tick }) {
  if (status === "sent") {
    return <Check className="size-3.5 text-tick" aria-label="Sent" />
  }
  if (status === "delivered") {
    return <CheckCheck className="size-3.5 text-tick" aria-label="Delivered" />
  }
  return <CheckCheck className="size-3.5 text-primary" aria-label="Read" />
}
