import { createContext, useContext } from "react"

export type User = { id: string; name: string; email: string }

export type Auth = {
  user: User | null // null = logged out
  login: (email: string, password: string) => Promise<void>
  signup: (name: string, email: string, password: string) => Promise<void>
  logout: () => Promise<void>
}

export const AuthContext = createContext<Auth | null>(null)

// The logged-in user and the log-in, sign-up and log-out actions, for any screen.
export function useAuth() {
  const auth = useContext(AuthContext)
  if (!auth) throw new Error("useAuth must be used inside <AuthProvider>")
  return auth
}
