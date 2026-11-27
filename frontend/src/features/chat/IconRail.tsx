import { Eye, Users } from "lucide-react"
import { Avatar } from "@/components/Avatar"
import { Logo } from "@/components/Logo"
import { cn } from "@/lib/utils"
import type { Section } from "@/features/status/SectionTabs"

type IconRailProps = {
  myName: string
  section: Section
  onSection: (section: Section) => void
  statusUnseen: boolean // a teal dot on Status: something I haven't watched
}

// The left column, from 768px: the logo, Chats and Status under it, and my avatar
// at the bottom. Phones have no rail; they switch with SectionTabs (D8, D41).
export function IconRail({ myName, section, onSection, statusUnseen }: IconRailProps) {
  const item = (name: Section, label: string, Icon: typeof Users, dot = false) => (
    <div className="relative flex justify-center">
      <button
        type="button"
        onClick={() => onSection(name)}
        aria-label={label}
        aria-pressed={section === name}
        className={cn(
          "relative flex size-14 items-center justify-center rounded-lg",
          section === name ? "bg-accent text-primary" : "text-rail-icon hover:text-muted-foreground",
        )}
      >
        <Icon className="size-5" />
        {dot && <span className="absolute top-3 right-3 size-2 rounded-full bg-primary" />}
      </button>
      {section === name && <span className="absolute inset-y-0 right-0 w-0.75 rounded-l bg-primary" />}
    </div>
  )

  return (
    <nav className="hidden w-24 shrink-0 flex-col border-r md:flex">
      <div className="flex h-20 items-center justify-center pt-4">
        <Logo className="size-9" />
      </div>

      <div className="mt-4 flex flex-col gap-2">
        {item("chats", "Chats", Users)}
        {item("status", "Status", Eye, statusUnseen && section !== "status")}
      </div>

      {/* Just a picture: nothing happens on click, so no hover or hand cursor */}
      <div className="mt-auto flex justify-center pb-6">
        <Avatar name={myName} tint="teal" />
      </div>
    </nav>
  )
}
