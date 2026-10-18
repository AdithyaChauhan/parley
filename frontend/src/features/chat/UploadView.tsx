import { FolderUp } from "lucide-react"

type UploadViewProps = {
  chatName: string
  isGroup: boolean
}

// Shown while a file is dragged over the conversation (reference-2).
// Screen only: dropping does nothing until v2 (D8).
export function UploadView({ chatName, isGroup }: UploadViewProps) {
  return (
    <div className="absolute inset-0 z-10 rounded-[inherit] bg-conversation/80 p-4 backdrop-blur-sm">
      <div className="flex h-full flex-col items-center justify-center rounded-panel border-2 border-dashed border-rail-icon text-center">
        <div className="flex size-56 items-center justify-center rounded-full border-2 border-dotted border-primary/40">
          <div className="flex size-26 items-center justify-center rounded-full bg-primary text-primary-foreground shadow-lg shadow-primary/30 ring-16 ring-accent">
            <FolderUp className="size-9" />
          </div>
        </div>
        <p className="mt-6 text-3xl font-medium">Upload your file</p>
        <p className="mt-3 text-muted-foreground">
          {isGroup ? "to the " : "to your chat with "}
          <span className="text-primary">{chatName}</span>
          {isGroup && " group"}
        </p>
      </div>
    </div>
  )
}
