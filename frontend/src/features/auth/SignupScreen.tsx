import { useState, type FormEvent } from "react"
import { Button } from "@/components/ui/button"
import { AuthCard } from "./AuthCard"
import { FormField } from "./FormField"
import { serverErrors } from "./serverErrors"
import { useAuth } from "./useAuth"
import { checkEmail, checkName, checkPassword } from "./validate"

// Sign-up: name, email and password. On success, App sends you to the chat screen.
export function SignupScreen() {
  const { signup } = useAuth()
  const [name, setName] = useState("")
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [errors, setErrors] = useState({ name: "", email: "", password: "" })
  const [formError, setFormError] = useState("")
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e: FormEvent) {
    e.preventDefault() // stop the browser reloading the page
    const found = { name: checkName(name), email: checkEmail(email), password: checkPassword(password) }
    setErrors(found)
    setFormError("")
    if (found.name || found.email || found.password) return

    setLoading(true)
    try {
      await signup(name, email, password)
    } catch (error) {
      const { fields, form } = serverErrors(error)
      setErrors({ name: fields.name ?? "", email: fields.email ?? "", password: fields.password ?? "" })
      setFormError(form)
      setLoading(false)
    }
  }

  return (
    <AuthCard title="Create your account" switchText="Have an account?" switchLabel="Log in" switchTo="/login">
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
        {formError && (
          <p role="alert" className="text-label text-destructive">
            {formError}
          </p>
        )}
        <Button type="submit" disabled={loading} className="mt-2 h-12 text-[length:var(--text-body)] disabled:opacity-80">
          {loading ? "Signing up..." : "Sign up"}
        </Button>
      </form>
    </AuthCard>
  )
}
