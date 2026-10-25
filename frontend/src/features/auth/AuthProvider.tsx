import { useEffect, useState, type ReactNode } from "react"
import { Logo } from "@/components/Logo"
import { api, refresh, setAccessToken, setOnLoggedOut } from "@/lib/api"
import { resendPush, turnOffPush } from "@/lib/push"
import { AuthContext, type Auth, type User } from "./useAuth"

// Knows who is logged in. The user and the access token live in memory only,
// never in localStorage (D16). On page load it uses the refresh cookie to
// log back in, and shows a simple loading screen until that's done.
export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [checking, setChecking] = useState(true)

  useEffect(() => {
    // api.ts calls this when a refresh says the session is over.
    setOnLoggedOut(() => setUser(null))

    async function restore() {
      try {
        if (await refresh()) {
          setUser(await api<User>("/auth/me"))
          resendPush().catch(() => {}) // never holds up the app
        }
      } catch {
        // Backend unreachable: show log-in. Its form says "Can't reach Parley" on submit.
      } finally {
        setChecking(false)
      }
    }
    restore()
  }, [])

  // Log-in and sign-up both reply with an access token; then we ask who we are.
  async function startSession(path: string, body: object) {
    const { access_token } = await api<{ access_token: string }>(path, { method: "POST", body })
    setAccessToken(access_token)
    setUser(await api<User>("/auth/me"))
    // This browser may still be subscribed for whoever was here before (D26).
    resendPush().catch(() => {})
  }

  const auth: Auth = {
    user,
    login: (email, password) => startSession("/auth/login", { email, password }),
    signup: (name, email, password) => startSession("/auth/signup", { name, email, password }),
    async logout() {
      // First, while we still have the access token: stop this browser
      // getting this user's notifications (a shared computer, D26).
      await turnOffPush().catch(() => {})
      try {
        await api("/auth/logout", { method: "POST" })
      } catch {
        // Even if the backend can't be reached, log out here in the browser.
      }
      setAccessToken(null)
      setUser(null)
    },
  }

  if (checking) {
    return (
      <main role="status" className="flex min-h-svh flex-col items-center justify-center gap-3 bg-background">
        <Logo className="size-12 animate-pulse" />
        <p className="text-sm text-muted-foreground">Loading...</p>
      </main>
    )
  }

  return <AuthContext.Provider value={auth}>{children}</AuthContext.Provider>
}
