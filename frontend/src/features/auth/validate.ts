// Checks that run in the browser before "sending" a form.
// Each returns an error message, or "" when the value is fine.
// The backend checks again when it arrives (T10, T12).

const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/ // something@something.something

export function checkName(name: string) {
  if (!name.trim()) return "Enter your name"
  if (name.trim().length < 2) return "Name must be at least 2 characters"
  return ""
}

export function checkEmail(email: string) {
  if (!email.trim()) return "Enter your email"
  if (!emailPattern.test(email.trim())) return "Enter a valid email, like name@example.com"
  return ""
}

export function checkPassword(password: string) {
  if (!password) return "Enter your password"
  if (password.length < 8) return "Password must be at least 8 characters"
  return ""
}
