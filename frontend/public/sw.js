// Retire the old worker, which cached API responses and returned HTML on failures.
self.addEventListener('install', (event) => event.waitUntil(self.skipWaiting()))
self.addEventListener('activate', (event) => {
  event.waitUntil((async () => {
    await caches.delete('tuberintel-shell-v1')
    await self.clients.claim()
    await self.registration.unregister()
  })())
})
