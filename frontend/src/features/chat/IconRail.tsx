import { ChartNoAxesColumn, ClipboardCheck, Eye, Gauge, Users, Video } from "lucide-react"
import { Avatar } from "@/components/Avatar"
import { Logo } from "@/components/Logo"
import { cn } from "@/lib/utils"

// Only "Chats" works for now. The other icons are placeholders.
const icons = [
  { label: "Dashboard", icon: Gauge },
  { label: "Tasks", icon: ClipboardCheck },
  { label: "Stories", icon: Eye },
  { label: "Chats", icon: Users },
  { label: "Stats", icon: ChartNoAxesColumn },
  { label: "Calls", icon: Video },
]
const activeLabel = "Chats"

// Desktop: a column on the left. Phone: a bar at the bottom.
export function IconRail({ myName }: { myName: string }) {
  return (
    <nav className="order-last flex h-16 shrink-0 border-t md:order-first md:h-auto md:w-24 md:flex-col md:border-t-0 md:border-r">
      <div className="hidden h-20 items-center justify-center pt-4 md:flex">
        <Logo className="size-9" />
      </div>

      <div className="flex flex-1 items-center md:flex-col md:justify-center md:gap-4">
        {icons.map(({ label, icon: Icon }) => {
          const active = label === activeLabel
          return (
            <div key={label} className="relative flex flex-1 justify-center md:w-full md:flex-none">
              <button
                type="button"
                aria-label={label}
                className={cn(
                  "flex size-11 items-center justify-center rounded-lg md:size-14",
                  active ? "bg-accent text-primary" : "text-rail-icon hover:text-muted-foreground",
                )}
              >
                <Icon className="size-5" />
              </button>
              {active && (
                <span className="absolute inset-x-3 -top-2.5 h-0.75 rounded-b bg-primary md:inset-x-auto md:inset-y-0 md:top-0 md:right-0 md:h-auto md:w-0.75 md:rounded-l md:rounded-br-none" />
              )}
            </div>
          )
        })}
      </div>

      <div className="hidden justify-center pb-6 md:flex">
        <Avatar name={myName} tint="teal" />
      </div>
    </nav>
  )
}
