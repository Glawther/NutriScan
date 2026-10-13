const CACHE_NAME = "nutriscan-v1.6.3";
const PRECACHE_ASSETS = [
  "/",
  "/manifest.json",
  "/css/style.css",
  "/static/css/style.css",
  "/js/app.js",
  "/js/app_tour.js",
  "/js/plate_scanner.js",
  "/js/barcode_cam.js",
  "/js/label_parser.js",
  "/js/share_export.js",
  "/static/js/app.js",
  "/static/js/app_tour.js",
  "/static/js/plate_scanner.js",
  "/static/js/barcode_cam.js",
  "/static/js/label_parser.js",
  "/static/js/share_export.js",
  "/samples/rotulo_whey.png",
  "/samples/rotulo_pasta_amendoim.png",
  "/samples/rotulo_pao_integral.png",
  "/samples/rotulo_iogurte_proteico.png",
  "/samples/pratos/prato_feito.png",
  "/samples/pratos/omelete_fitness.png",
  "/samples/pratos/salmao_legumes.png",
  "/samples/pratos/acai_banana.png",
  "/static/samples/rotulo_whey.png",
  "/static/samples/rotulo_pasta_amendoim.png",
  "/static/samples/rotulo_pao_integral.png",
  "/static/samples/rotulo_iogurte_proteico.png",
  "/static/samples/pratos/prato_feito.png",
  "/static/samples/pratos/omelete_fitness.png",
  "/static/samples/pratos/salmao_legumes.png",
  "/static/samples/pratos/acai_banana.png"
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(async (cache) => {
      // Use individual puts with try/catch to ensure optional assets do not fail the precache
      await Promise.all(
        PRECACHE_ASSETS.map((asset) =>
          cache.add(asset).catch(() => {})
        )
      );
    })
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
  const url = new URL(event.request.url);

  // Skip non-http schemes (e.g. chrome-extension, file)
  if (!url.protocol.startsWith("http")) return;

  // For API endpoints, prefer network first, no offline crash
  if (url.pathname.startsWith("/api/")) {
    return;
  }

  // Cache-first strategy for static assets and HTML
  event.respondWith(
    caches.match(event.request, { ignoreSearch: true }).then((cachedResponse) => {
      if (cachedResponse) {
        return cachedResponse;
      }
      return fetch(event.request)
        .then((networkResponse) => {
          if (networkResponse && networkResponse.status === 200) {
            const copy = networkResponse.clone();
            caches.open(CACHE_NAME).then((cache) => {
              cache.put(event.request, copy).catch(() => {});
            });
          }
          return networkResponse;
        })
        .catch(() => {
          if (event.request.mode === "navigate") {
            return caches.match("/");
          }
        });
    })
  );
});
