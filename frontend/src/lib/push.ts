// Browser notifications (D26): turn them on (only on a click), re-send after
// log-in, and turn them off on log-out. The service worker is public/sw.js.
import { api } from "./api"

// Incognito windows and some browsers can't get pushes at all.
export function pushSupported() {
  return "serviceWorker" in navigator && "PushManager" in window && "Notification" in window
}

// The public key arrives as base64url text; the browser wants raw bytes.
function keyBytes(base64url: string) {
  const base64 = base64url.replace(/-/g, "+").replace(/_/g, "/") + "=".repeat((4 - (base64url.length % 4)) % 4)
  return Uint8Array.from(atob(base64), (char) => char.charCodeAt(0))
}

// This browser's subscription, if it has one (from an earlier click).
async function currentSubscription() {
  if (!pushSupported()) return null
  const registration = await navigator.serviceWorker.getRegistration()
  return (await registration?.pushManager.getSubscription()) ?? null
}

// "on": this browser gets pushes. "off": the button can ask. "blocked": the
// user said no, and only the browser's site settings can undo that.
export type PushState = "on" | "off" | "blocked" | "unsupported"

export async function pushState(): Promise<PushState> {
  if (!pushSupported()) return "unsupported"
  if (Notification.permission === "denied") return "blocked"
  return Notification.permission === "granted" && (await currentSubscription()) ? "on" : "off"
}

// The click: the browser asks, the push service gives an address and two
// keys, and our server saves them for the logged-in user.
export async function turnOnPush(): Promise<PushState> {
  if ((await Notification.requestPermission()) !== "granted") return pushState()
  const { public_key } = await api<{ public_key: string }>("/push/key")
  await navigator.serviceWorker.register("/sw.js")
  // ready: the service worker is running, which subscribing needs.
  const registration = await navigator.serviceWorker.ready
  const subscription =
    (await registration.pushManager.getSubscription()) ??
    (await registration.pushManager.subscribe({ userVisibleOnly: true, applicationServerKey: keyBytes(public_key) }))
  await api("/push/subscribe", { method: "POST", body: subscription.toJSON() })
  return "on"
}

// After log-in: this browser may still be subscribed for whoever was here
// before, so move it to the new user. Never creates one without the click.
export async function resendPush() {
  if (!pushSupported() || Notification.permission !== "granted") return
  const subscription = await currentSubscription()
  if (subscription) await api("/push/subscribe", { method: "POST", body: subscription.toJSON() })
}

// Log-out: delete our row first (it needs the access token), then unsubscribe
// in the browser. If the delete fails, the push service answers 410 next
// time and the worker deletes the row then.
export async function turnOffPush() {
  const subscription = await currentSubscription()
  if (!subscription) return
  try {
    await api("/push/subscribe", { method: "DELETE", body: { endpoint: subscription.endpoint } })
  } finally {
    await subscription.unsubscribe()
  }
}
