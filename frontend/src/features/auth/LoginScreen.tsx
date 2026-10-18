import { useState, type FormEvent } from "react"
import { Button } from "@/components/ui/button"
import { AuthCard } from "./AuthCard"
import { FormField } from "./FormField"
import { checkEmail, checkPassword } from "./validate"

type LoginScreenProps = {
  onLogin: () => void
  onSwitch: () => void
}

// Log-in: email and password. Fake for now: a correct form opens the chat screen (T12 makes it real).
export function LoginScreen({ onLogin, onSwitch }: LoginScreenProps) {
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [errors, setErrors] = useState({ email: "", password: "" })
  const [loading, setLoading] = useState(false)

  function handleSubmit(e: FormEvent) {
    e.preventDefault() // stop the browser reloading the page
    const found = { email: checkEmail(email), password: checkPassword(password) }
    setErrors(found)
    if (found.email || found.password) return

    setLoading(true)
    // Fake "sending": wait about 1 second, then open the chat
    setTimeout(onLogin, 1000)
  }

  return (
    <AuthCard title="Welcome back" switchText="No account?" switchLabel="Sign up" onSwitch={onSwitch}>
      <form onSubmit={handleSubmit} noValidate className="mt-8 flex flex-col gap-5">
        <FormField
          id="email"
          label="Email"
          type="email"
          autoComplete="email"
          value={email}
          onChange={(value) => {
            setEmail(value)
            setErrors((prev) => ({ ...prev, email: "" }))
          }}
          error={errors.email}
        />
        <FormField
          id="password"
          label="Password"
          type="password"
          autoComplete="current-password"
          value={password}
          onChange={(value) => {
            setPassword(value)
            setErrors((prev) => ({ ...prev, password: "" }))
          }}
          error={errors.password}
        />
        <Button type="submit" disabled={loading} className="mt-2 h-12 text-[length:var(--text-body)] disabled:opacity-80">
          {loading ? "Logging in..." : "Log in"}
        </Button>
      </form>
    </AuthCard>
  )
}
