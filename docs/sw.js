// Red primero; si no hay señal (en obra), muestra lo último visto.
const CACHE = "vertice-v1";
self.addEventListener("install", e => { self.skipWaiting(); e.waitUntil(caches.open(CACHE).then(c => c.addAll(["./", "./index.html", "./manifest.json", "./icon-192.png"]))); });
self.addEventListener("activate", e => e.waitUntil(self.clients.claim()));
self.addEventListener("fetch", e => {
  if (e.request.method !== "GET") return;
  const url = new URL(e.request.url);
  const pesado = /\.(zip|dxf|pdf)$/i.test(url.pathname);
  e.respondWith(fetch(e.request).then(r => {
    if (r.ok && !pesado && url.origin === location.origin) { const cp = r.clone(); caches.open(CACHE).then(c => c.put(e.request, cp)); }
    return r;
  }).catch(() => caches.match(e.request).then(m => m || caches.match("./index.html"))));
});
