import {
  ArrowLeft,
  ChevronLeft,
  ChevronRight,
  Clapperboard,
  EllipsisVertical,
  FileText,
  Files,
  Folder,
  ImageIcon,
  Link,
} from "lucide-react"
import { Avatar } from "@/components/Avatar"
import { fakeFiles } from "@/data/fake"
import { cn } from "@/lib/utils"
import { tintFor, type ChatSummary } from "./types"

const fileTypes = [
  { key: "documents", label: "Documents", icon: FileText, tile: "bg-file-purple text-file-purple-icon" },
  { key: "photos", label: "Photos", icon: ImageIcon, tile: "bg-file-yellow text-file-yellow-icon" },
  { key: "movies", label: "Movies", icon: Clapperboard, tile: "bg-file-teal text-file-teal-icon" },
  { key: "other", label: "Other", icon: Files, tile: "bg-file-red text-file-red-icon" },
] as const

type SidePanelProps = {
  chat: ChatSummary
  open: boolean
  onToggle: () => void
  onBack: () => void
  phoneVisible: boolean
}

// The right panel: the open chat's real name and member count, and its shared files
// (reference-1). The file tiles stay fake until v2.
// Folded, it becomes a thin strip of icons (reference-3). On a phone it is always open, full screen.
export function SidePanel({ chat, open, onToggle, onBack, phoneVisible }: SidePanelProps) {
  const tint = tintFor(chat.id)

  return (
    <>
      <aside
        className={cn(
          "min-h-0 flex-1 flex-col overflow-y-auto px-4 scrollbar-thin md:w-85 md:flex-none",
          phoneVisible ? "flex" : "hidden",
          open && "md:flex",
          !open && "md:hidden",
        )}
      >
        {/* Phone only: back arrow and title. On desktop there is no header. */}
        <header className="flex h-20 shrink-0 items-center gap-4 border-b pt-4 md:hidden">
          <button
            type="button"
            onClick={onBack}
            aria-label="Back to the conversation"
            className="flex size-10 items-center justify-center rounded-lg bg-row-selected text-muted-foreground"
          >
            <ArrowLeft className="size-4" />
          </button>
          <h2 className="text-header">Shared files</h2>
        </header>

        <div className="relative flex flex-col items-center pt-4 pb-5 md:pt-6">
          <button
            type="button"
            onClick={onToggle}
            aria-label="Fold the panel"
            className="absolute top-5 right-0 hidden size-8 items-center justify-center rounded-lg text-muted-foreground hover:bg-row-selected md:flex"
          >
            <ChevronRight className="size-5" />
          </button>
          <Avatar name={chat.name} tint={tint} size="lg" />
          <p className="mt-2 text-name">{chat.name}</p>
          {/* Every chat is a direct chat (two people) until groups in v2 */}
          <p className="text-sm text-muted-foreground">{chat.kind === "direct" ? "2 members" : "Group"}</p>
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div className="relative rounded-lg bg-accent p-4">
            <span className="absolute top-3 right-3 flex size-4 items-center justify-center rounded-full bg-card">
              <span className="size-2 rounded-full bg-primary" />
            </span>
            <p className="pl-9 text-label">All files</p>
            <p className="flex items-center gap-3 text-3xl">
              <Folder className="size-6 fill-primary text-primary" />
              {fakeFiles.all}
            </p>
          </div>
          <div className="relative rounded-lg bg-row-selected p-4">
            <span className="absolute top-3 right-3 size-4 rounded-full bg-card" />
            <p className="pl-9 text-label text-muted-foreground">All links</p>
            <p className="flex items-center gap-3 text-3xl">
              <Link className="size-6 text-rail-icon" />
              {fakeFiles.links}
            </p>
          </div>
        </div>

        <div className="mt-6 mb-2 flex items-center justify-between">
          <h3>File type</h3>
          <button type="button" aria-label="More" className="text-muted-foreground">
            <EllipsisVertical className="size-4" />
          </button>
        </div>

        <ul className="pb-4">
          {fileTypes.map(({ key, label, icon: Icon, tile }) => (
            <li key={key}>
              <button type="button" className="flex w-full items-center gap-4 rounded-lg py-2 text-left">
                <span className={cn("flex size-12 items-center justify-center rounded-lg", tile)}>
                  <Icon className="size-5" />
                </span>
                <span className="flex-1">
                  <span className="block font-medium">{label}</span>
                  <span className="block text-label text-muted-foreground">
                    {fakeFiles[key].count} files, {fakeFiles[key].size}
                  </span>
                </span>
                <ChevronRight className="size-4 text-muted-foreground" />
              </button>
            </li>
          ))}
        </ul>
      </aside>

      {/* Folded: a thin strip of icons, desktop only */}
      <aside className={cn("w-18 shrink-0 flex-col items-center", open ? "hidden" : "hidden md:flex")}>
        <div className="flex w-full shrink-0 justify-center pt-5">
          <button
            type="button"
            onClick={onToggle}
            aria-label="Open the panel"
            className="flex size-8 items-center justify-center rounded-lg text-muted-foreground hover:bg-row-selected"
          >
            <ChevronLeft className="size-5" />
          </button>
        </div>
        <div className="mt-4">
          <Avatar name={chat.name} tint={tint} />
        </div>
        <p className="mt-6 mb-3 text-label text-muted-foreground">Files</p>
        <div className="flex flex-col gap-4">
          {fileTypes.map(({ key, label, icon: Icon, tile }) => (
            <span key={key} title={label} className={cn("flex size-10 items-center justify-center rounded-lg", tile)}>
              <Icon className="size-4" />
            </span>
          ))}
          <span title="Links" className="flex size-10 items-center justify-center rounded-lg bg-accent text-primary">
            <Link className="size-4" />
          </span>
        </div>
      </aside>
    </>
  )
}
