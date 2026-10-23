import { ApiError, isUnreachable } from "@/lib/api"

type FormErrors = {
  fields: Record<string, string> // shown under that field
  form: string // shown above the button, for problems that aren't about one field
}

// Turns a failed log-in or sign-up into messages for the form (T7 style).
export function serverErrors(error: unknown): FormErrors {
  if (error instanceof ApiError) {
    if (error.status === 401) return { fields: { password: "Wrong email or password." }, form: "" }
    if (error.status === 409) return { fields: { email: "That email is already taken." }, form: "" }
    if (error.status === 429) {
      // Locked for a while (D24): Retry-After says how long, in seconds
      const minutes = Math.max(1, Math.ceil((error.retryAfter ?? 60) / 60))
      return { fields: {}, form: `Too many tries. Try again in ${minutes} minute${minutes === 1 ? "" : "s"}.` }
    }
    if (error.status === 422) {
      const fields = fieldProblems(error.body)
      if (Object.keys(fields).length > 0) return { fields, form: "" }
    }
  }
  if (isUnreachable(error)) return { fields: {}, form: "Can't reach Parley. Try again." }
  return { fields: {}, form: "Something went wrong. Try again." }
}

// A 422 reply lists each problem with where it was:
// { "detail": [{ "loc": ["body", "email"], "msg": "..." }] }
function fieldProblems(body: unknown): Record<string, string> {
  const detail = (body as { detail?: { loc: (string | number)[]; msg: string }[] } | null)?.detail
  const fields: Record<string, string> = {}
  for (const problem of Array.isArray(detail) ? detail : []) {
    const field = String(problem.loc.at(-1))
    fields[field] ??= problem.msg // keep the first problem per field
  }
  return fields
}
