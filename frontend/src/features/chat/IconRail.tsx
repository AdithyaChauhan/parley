import { Users } from "lucide-react"
import { Avatar } from "@/components/Avatar"
import { Logo } from "@/components/Logo"

// The left column, from 768px: the logo, Chats right under it, and my avatar at the bottom.
// Other sections stay hidden until they work, and phones have no rail at all (D8).
export function IconRail({ myName }: { myName: string }) {
  return (
    <nav className="hidden w-24 shrink-0 flex-col border-r md:flex">
      <div className="flex h-20 items-center justify-center pt-4">
        <Logo className="size-9" />
      </div>

      {/* Chats is the only section, so it's always the active one: a marker, not a button */}
      <div className="relative mt-4 flex justify-center">
        <div role="img" aria-label="Chats" className="flex size-14 items-center justify-center rounded-lg bg-accent text-primary">
          <Users className="size-5" />
        </div>
        <span className="absolute inset-y-0 right-0 w-0.75 rounded-l bg-primary" />
      </div>

      {/* Just a picture: nothing happens on click, so no hover or hand cursor */}
      <div className="mt-auto flex justify-center pb-6">
        <Avatar name={myName} tint="teal" />
      </div>
    </nav>
  )
}
