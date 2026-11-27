import { cn } from "@/lib/utils"

export type Section = "chats" | "status"

// Phones have no rail (D8), so Chats and Status switch here, at the top of the
// list. From 768px the rail does this, and these are hidden.
export function SectionTabs({
  section,
  onSection,
  unseen,
  className,
}: {
  section: Section
  onSection: (section: Section) => void
  unseen: boolean // a teal dot on Status: something I haven't watched
  className?: string
}) {
  const tab = (name: Section, label: string, dot = false) => (
    <button
      type="button"
      onClick={() => onSection(name)}
      aria-pressed={section === name}
      className={cn(
        "relative flex-1 rounded-md py-2 text-sm",
        section === name ? "bg-card font-medium text-foreground shadow-sm" : "text-muted-foreground",
      )}
    >
      {label}
      {dot && (
        <span aria-label="New updates" className="absolute top-2 ml-1 inline-block size-2 rounded-full bg-primary" />
      )}
    </button>
  )
  return (
    <div className={cn("flex gap-1 rounded-lg bg-search p-1 md:hidden", className)}>
      {tab("chats", "Chats")}
      {tab("status", "Status", unseen && section !== "status")}
    </div>
  )
}
