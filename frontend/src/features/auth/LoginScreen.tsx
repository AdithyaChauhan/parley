import { useState, type FormEvent } from "react"
import { Button } from "@/components/ui/button"
import { AuthCard } from "./AuthCard"
import { FormField } from "./FormField"
import { serverErrors } from "./serverErrors"
import { useAuth } from "./useAuth"
import { checkEmail, checkPassword } from "./validate"

// Log-in: email and password. On success, App sends you to the chat screen.
export function LoginScreen() {
  const { login } = useAuth()
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [errors, setErrors] = useState({ email: "", password: "" })
  const [formError, setFormError] = useState("")
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e: FormEvent) {
    e.preventDefault() // stop the browser reloading the page
    const found = { email: checkEmail(email), password: checkPassword(password) }
    setErrors(found)
    setFormError("")
    if (found.email || found.password) return

    setLoading(true)
    try {
      await login(email, password)
    } catch (error) {
      const { fields, form } = serverErrors(error)
      setErrors({ email: fields.email ?? "", password: fields.password ?? "" })
      setFormError(form)
      setLoading(false)
    }
  }

  return (
    <AuthCard title="Welcome back" switchText="No account?" switchLabel="Sign up" switchTo="/signup">
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
        {formError && (
          <p role="alert" className="text-label text-destructive">
            {formError}
          </p>
        )}
        <Button type="submit" disabled={loading} className="mt-2 h-12 text-[length:var(--text-body)] disabled:opacity-80">
          {loading ? "Logging in..." : "Log in"}
        </Button>
      </form>
    </AuthCard>
  )
}
