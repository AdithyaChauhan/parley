// Parley's service worker (D26). The browser keeps this small script around
// even when every Parley tab is closed, and wakes it up when a push arrives.

// A new version of this file takes over at once, instead of waiting until
// every Parley tab has closed.
self.addEventListener("install", () => self.skipWaiting())

self.addEventListener("push", (event) => {
  // The title and the chat id only, never the message text (D12).
  const { title, chat_id } = event.data ? event.data.json() : { title: "Parley" }
  event.waitUntil(
    (async () => {
      // One chat, one notification. A replacement with the same tag is
      // silent on Windows (an old one left in the list would hide every new
      // message), so close the old one and show a new one, which pops up.
      const old = await self.registration.getNotifications({ tag: chat_id })
      old.forEach((notification) => notification.close())
      await self.registration.showNotification(title, {
        tag: chat_id,
        renotify: true,
        data: { chat_id },
      })
    })(),
  )
})

// A click focuses an open Parley tab, or opens one.
self.addEventListener("notificationclick", (event) => {
  event.notification.close()
  event.waitUntil(
    (async () => {
      const tabs = await self.clients.matchAll({ type: "window", includeUncontrolled: true })
      const parley = tabs.find((tab) => new URL(tab.url).origin === self.location.origin)
      if (parley) return parley.focus()
      return self.clients.openWindow("/")
    })(),
  )
})
