// Enhanced service worker for offline caching and performance optimization
const CACHE_NAME = 'smc-trading-cache-v2';
const STATIC_CACHE = 'smc-static-v2';
const DYNAMIC_CACHE = 'smc-dynamic-v2';

const STATIC_ASSETS = [
  '/',
  '/index.html',
  '/favicon.svg',
  '/manifest.json'
];

// Cache strategies
const CACHE_STRATEGIES = {
  static: ['/', '/index.html', '/favicon.svg'],
  staleWhileRevalidate: ['/assets/', '.js', '.css', '.woff2'],
  networkFirst: ['/api/']
};

self.addEventListener('install', (event) => {
  event.waitUntil(
    Promise.all([
      caches.open(STATIC_CACHE).then(cache => cache.addAll(STATIC_ASSETS)),
      self.skipWaiting()
    ])
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    Promise.all([
      caches.keys().then(keys => 
        Promise.all(
          keys.filter(key => 
            key !== STATIC_CACHE && 
            key !== DYNAMIC_CACHE
          ).map(key => caches.delete(key))
        )
      ),
      self.clients.claim()
    ])
  );
});

self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Skip non-GET requests
  if (request.method !== 'GET') return;

  // API requests - Network first
  if (url.pathname.startsWith('/api/')) {
    event.respondWith(networkFirst(request));
    return;
  }

  // Static assets - Cache first
  if (CACHE_STRATEGIES.static.some(path => url.pathname === path)) {
    event.respondWith(cacheFirst(request));
    return;
  }

  // JS/CSS/Fonts - Stale while revalidate
  if (CACHE_STRATEGIES.staleWhileRevalidate.some(ext => 
    url.pathname.includes(ext) || url.pathname.startsWith('/assets/')
  )) {
    event.respondWith(staleWhileRevalidate(request));
    return;
  }

  // Default - Network first with cache fallback
  event.respondWith(networkFirst(request));
});

// Cache strategies implementation
async function cacheFirst(request) {
  const cached = await caches.match(request);
  return cached || fetch(request);
}

async function networkFirst(request) {
  try {
    const response = await fetch(request);
    if (response.ok) {
      const cache = await caches.open(DYNAMIC_CACHE);
      cache.put(request, response.clone());
    }
    return response;
  } catch (error) {
    const cached = await caches.match(request);
    return cached || new Response('Offline', { status: 503 });
  }
}

async function staleWhileRevalidate(request) {
  const cached = await caches.match(request);
  const fetchPromise = fetch(request).then(response => {
    if (response.ok) {
      const cache = caches.open(DYNAMIC_CACHE);
      cache.then(c => c.put(request, response.clone()));
    }
    return response;
  }).catch(() => cached);

  return cached || fetchPromise;
}


