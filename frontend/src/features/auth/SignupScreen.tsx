import { useState, type FormEvent } from "react"
import { Button } from "@/components/ui/button"
import { AuthCard } from "./AuthCard"
import { FormField } from "./FormField"
import { checkEmail, checkName, checkPassword } from "./validate"

type SignupScreenProps = {
  onSignup: () => void
  onSwitch: () => void
}

// Sign-up: name, email and password. Fake for now: a correct form opens the chat screen (T12 makes it real).
export function SignupScreen({ onSignup, onSwitch }: SignupScreenProps) {
  const [name, setName] = useState("")
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [errors, setErrors] = useState({ name: "", email: "", password: "" })
  const [loading, setLoading] = useState(false)

  function handleSubmit(e: FormEvent) {
    e.preventDefault() // stop the browser reloading the page
    const found = { name: checkName(name), email: checkEmail(email), password: checkPassword(password) }
    setErrors(found)
    if (found.name || found.email || found.password) return

    setLoading(true)
    // Fake "sending": wait about 1 second, then open the chat
    setTimeout(onSignup, 1000)
  }

  return (
    <AuthCard title="Create your account" switchText="Have an account?" switchLabel="Log in" onSwitch={onSwitch}>
      <form onSubmit={handleSubmit} noValidate className="mt-8 flex flex-col gap-5">
        <FormField
          id="name"
          label="Name"
          autoComplete="name"
          value={name}
          onChange={(value) => {
            setName(value)
            setErrors((prev) => ({ ...prev, name: "" }))
          }}
          error={errors.name}
        />
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
          autoComplete="new-password"
          value={password}
          onChange={(value) => {
            setPassword(value)
            setErrors((prev) => ({ ...prev, password: "" }))
          }}
          error={errors.password}
        />
        <Button type="submit" disabled={loading} className="mt-2 h-12 text-[length:var(--text-body)] disabled:opacity-80">
          {loading ? "Signing up..." : "Sign up"}
        </Button>
      </form>
    </AuthCard>
  )
}
