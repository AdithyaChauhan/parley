import { useState } from "react"
import { Eye, EyeOff } from "lucide-react"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { cn } from "@/lib/utils"

type FormFieldProps = {
  id: string
  label: string
  type?: "text" | "email" | "password"
  autoComplete: string
  value: string
  onChange: (value: string) => void
  error: string
}

// One form field: a label, a soft grey input (like the search box) and a red error under it.
// A password field also gets an eye button to show or hide what you typed.
// Note: text-[length:var(--text-body)] is our 15px body size. The "length:" part tells cn() it is a
// size, not a color; plain text-body would make cn() drop shadcn's own text classes.
export function FormField({ id, label, type = "text", autoComplete, value, onChange, error }: FormFieldProps) {
  const [shown, setShown] = useState(false)
  const isPassword = type === "password"
  const errorId = `${id}-error`

  return (
    <div className="flex flex-col gap-2">
      <Label htmlFor={id}>{label}</Label>
      <div className="relative">
        <Input
          id={id}
          type={isPassword && shown ? "text" : type}
          autoComplete={autoComplete}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          aria-invalid={error ? true : undefined}
          aria-describedby={error ? errorId : undefined}
          className={cn("h-12 border-transparent bg-search px-4 text-[length:var(--text-body)] md:text-[length:var(--text-body)]", isPassword && "pr-12")}
        />
        {isPassword && (
          <button
            type="button"
            onClick={() => setShown((s) => !s)}
            aria-label={shown ? "Hide password" : "Show password"}
            className="absolute inset-y-0 right-0 flex w-12 items-center justify-center text-muted-foreground hover:text-foreground"
          >
            {shown ? <EyeOff className="size-4" /> : <Eye className="size-4" />}
          </button>
        )}
      </div>
      {error && (
        <p id={errorId} className="text-label text-destructive">
          {error}
        </p>
      )}
    </div>
  )
}
