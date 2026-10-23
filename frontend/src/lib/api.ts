// The one place that talks to the backend. Every path here is under /api,
// which Vite passes on to FastAPI (D17).
//
// The access token lives only in this variable, in memory (D16). A page reload
// forgets it, and AuthProvider gets a new one from the refresh cookie.
let accessToken: string | null = null

// AuthProvider sets this, so we can tell it when the session is really over.
let onLoggedOut = () => {}

export function setAccessToken(token: string | null) {
  accessToken = token
}

export function setOnLoggedOut(callback: () => void) {
  onLoggedOut = callback
}

// A request that didn't work. status 0 means the backend couldn't be reached at all.
export class ApiError extends Error {
  status: number
  body: unknown
  // For a 429 "too many" (D24): seconds to wait before trying again, from the Retry-After header
  retryAfter: number | null

  constructor(status: number, body: unknown, retryAfter: number | null = null) {
    super(`Request failed with status ${status}`)
    this.status = status
    this.body = body
    this.retryAfter = retryAfter
  }
}

// The backend is stopped or broken. (When FastAPI is down, Vite's proxy answers with a 5xx.)
export function isUnreachable(error: unknown) {
  return error instanceof ApiError && (error.status === 0 || error.status >= 500)
}

type Options = { method?: string; body?: unknown }

async function send(path: string, { method = "GET", body }: Options): Promise<Response> {
  const headers = new Headers()
  if (accessToken) headers.set("Authorization", `Bearer ${accessToken}`)
  if (body !== undefined) headers.set("Content-Type", "application/json")

  try {
    return await fetch(`/api${path}`, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
    })
  } catch {
    throw new ApiError(0, null) // no answer at all: network down
  }
}

async function readBody(response: Response): Promise<unknown> {
  try {
    return await response.json()
  } catch {
    return null // empty or not JSON
  }
}

// Retry-After in whole seconds, or null if the reply has none
function readRetryAfter(response: Response): number | null {
  const seconds = Number(response.headers.get("Retry-After"))
  return seconds > 0 ? seconds : null
}

// --- Refresh: swap the refresh cookie for a new access token ---

const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms))

let refreshing: Promise<boolean> | null = null

async function refreshOnce(): Promise<boolean> {
  let response = await send("/auth/refresh", { method: "POST" })
  if (response.status === 401) {
    // Another tab may have just swapped the cookie for a new one. Wait a
    // moment, then try once more: the browser will send the newest cookie.
    await sleep(300)
    response = await send("/auth/refresh", { method: "POST" })
  }

  if (response.status === 401) return false // the session is really over
  if (!response.ok) throw new ApiError(response.status, await readBody(response))

  const { access_token } = (await response.json()) as { access_token: string }
  accessToken = access_token
  return true
}

// Only one refresh runs at a time. Anyone who asks while one is running
// waits for that same one, so the cookie is never swapped twice at once.
// Returns false when the session is over (log in again).
export function refresh(): Promise<boolean> {
  if (!refreshing) {
    refreshing = refreshOnce().finally(() => {
      refreshing = null
    })
  }
  return refreshing
}

// --- Normal requests ---

// Sends a request and returns the reply's JSON (null for an empty reply).
// Throws ApiError if it didn't work.
export async function api<T>(path: string, options: Options = {}): Promise<T> {
  const sentToken = accessToken
  let response = await send(path, options)

  // A 401 with a token usually means the 15-minute access token ran out:
  // get a new one and try once more. (Without a token, 401 is the real answer,
  // like "wrong email or password".)
  if (response.status === 401 && sentToken) {
    // If another request already got a new token while we waited, just use it.
    const renewed = accessToken !== sentToken || (await refresh())
    if (renewed) {
      response = await send(path, options)
    } else {
      accessToken = null
      onLoggedOut()
    }
  }

  if (!response.ok) throw new ApiError(response.status, await readBody(response), readRetryAfter(response))
  return (response.status === 204 ? null : await response.json()) as T
}
