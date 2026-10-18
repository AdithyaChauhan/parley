import { cn } from "@/lib/utils"
import type { Tint } from "@/data/fake"

const sizes = {
  sm: "size-8 text-[11px]",
  md: "size-10 text-[13px]",
  lg: "size-16 text-[20px]",
}

const tints: Record<Tint, string> = {
  teal: "bg-file-teal text-file-teal-icon",
  purple: "bg-file-purple text-file-purple-icon",
  yellow: "bg-file-yellow text-file-yellow-icon",
  red: "bg-file-red text-file-red-icon",
}

// "Mira Patel" -> "MP"
function initials(name: string) {
  return name
    .split(" ")
    .map((word) => word[0])
    .join("")
    .slice(0, 2)
    .toUpperCase()
}

type AvatarProps = {
  name: string
  tint: Tint
  size?: keyof typeof sizes
  online?: boolean
}

// A round avatar with initials on a soft tint (no photos, D8)
export function Avatar({ name, tint, size = "md", online = false }: AvatarProps) {
  return (
    <div
      className={cn(
        "relative flex shrink-0 items-center justify-center rounded-full font-medium",
        sizes[size],
        tints[tint],
      )}
    >
      {initials(name)}
      {online && (
        <span
          className={cn(
            "absolute rounded-full bg-online ring-card",
            size === "lg" ? "right-0.5 bottom-0.5 size-3 ring-2" : "right-0 bottom-0 size-2.5 ring-2",
          )}
        />
      )}
    </div>
  )
}
