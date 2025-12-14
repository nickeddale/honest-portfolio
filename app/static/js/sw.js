const CACHE_NAME = 'honest-portfolio-v3';
const STATIC_ASSETS = [
    '/',
    '/static/index.html',
    '/static/js/app.js',
    '/static/css/styles.css',
    'https://cdn.jsdelivr.net/npm/chart.js'
];

// Install event
self.addEventListener('install', event => {
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then(cache => cache.addAll(STATIC_ASSETS))
            .then(() => self.skipWaiting())
    );
});

// Activate event
self.addEventListener('activate', event => {
    event.waitUntil(
        caches.keys().then(keys => {
            return Promise.all(
                keys.filter(key => key !== CACHE_NAME)
                    .map(key => caches.delete(key))
            );
        }).then(() => self.clients.claim())
    );
});

// Fetch event - Network first, fall back to cache
self.addEventListener('fetch', event => {
    // Pass non-GET requests through to the network
    if (event.request.method !== 'GET') {
        event.respondWith(fetch(event.request));
        return;
    }

    // For API requests, always go to network
    if (event.request.url.includes('/api/')) {
        event.respondWith(
            fetch(event.request)
                .catch(() => new Response(JSON.stringify({ error: 'Offline' }), {
                    headers: { 'Content-Type': 'application/json' }
                }))
        );
        return;
    }

    // For static assets, try cache first, then network
    event.respondWith(
        caches.match(event.request)
            .then(response => response || fetch(event.request))
            .catch(() => caches.match('/static/index.html'))
    );
});
