import type { ReactNode } from "react"
import { Link } from "react-router"
import { Logo } from "@/components/Logo"

type AuthCardProps = {
  title: string
  children: ReactNode
  switchText: string
  switchLabel: string
  switchTo: string // the other page's address
}

// The white card on the blue-grey page, shared by log-in and sign-up (screens.md).
// On a phone it fills the width with a 16px gap on each side.
export function AuthCard({ title, children, switchText, switchLabel, switchTo }: AuthCardProps) {
  return (
    <main className="flex min-h-dvh items-center justify-center bg-background px-4 py-8">
      <div className="w-full max-w-100 rounded-card bg-card px-6 py-10 shadow-sm shadow-foreground/5 sm:px-10">
        <Logo className="mx-auto size-12" />
        <h1 className="mt-4 text-center text-header">{title}</h1>
        {children}
        <p className="mt-6 text-center text-sm text-muted-foreground">
          {switchText}{" "}
          <Link to={switchTo} className="font-medium text-primary hover:underline">
            {switchLabel}
          </Link>
        </p>
      </div>
    </main>
  )
}
