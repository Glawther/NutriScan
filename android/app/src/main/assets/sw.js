const CACHE_NAME = "nutriscan-v1.6.2";
const ASSETS = [
  "/",
  "/static/css/style.css",
  "/static/js/app.js",
  "/static/js/app_tour.js",
  "/static/js/plate_scanner.js",
  "/static/js/barcode_cam.js",
  "/static/js/label_parser.js",
  "/static/js/share_export.js",
  "/manifest.json"
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(ASSETS)).catch(() => {})
  );
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener("fetch", (event) => {
  if (event.request.method !== "GET") return;
  event.respondWith(
    fetch(event.request).catch(() => caches.match(event.request))
  );
});
