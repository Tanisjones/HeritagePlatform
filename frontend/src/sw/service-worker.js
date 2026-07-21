/* eslint-disable no-restricted-globals */

import { clientsClaim } from 'workbox-core'
import { cleanupOutdatedCaches, createHandlerBoundToURL, precacheAndRoute } from 'workbox-precaching'
import { BackgroundSyncPlugin } from 'workbox-background-sync'
import { registerRoute } from 'workbox-routing'
import { CacheFirst, NetworkFirst, NetworkOnly } from 'workbox-strategies'
import { CacheableResponsePlugin } from 'workbox-cacheable-response'
import { ExpirationPlugin } from 'workbox-expiration'

// Activate a new SW immediately and take control of open clients. Required
// under the injectManifest strategy: vite-plugin-pwa's `registerType: autoUpdate`
// only injects skipWaiting/clientsClaim for generateSW, so we must do it here or
// updates would stall in "waiting" until every tab closes (serving a stale shell).
self.skipWaiting()
clientsClaim()

// Precache Vite build assets (app shell)
precacheAndRoute(self.__WB_MANIFEST)
cleanupOutdatedCaches()

// SPA navigation fallback to index.html — but NEVER for backend-owned paths
// (Django admin, API, static/media), which nginx proxies to the backend.
// Without the denylist the fallback serves the SPA shell for /admin/.
//
// Match whole path segments, not raw prefixes: city slugs are top-level URL
// segments now, so a bare startsWith('/media') would also swallow a perfectly
// valid city like /mediana-de-aragon and break it offline.
const BACKEND_PATH_SEGMENTS = ['admin', 'api', 'static', 'media']
const isBackendPath = (pathname) =>
  BACKEND_PATH_SEGMENTS.some(
    (segment) => pathname === `/${segment}` || pathname.startsWith(`/${segment}/`),
  )
registerRoute(
  ({ request, url }) => request.mode === 'navigate' && !isBackendPath(url.pathname),
  createHandlerBoundToURL('/index.html'),
)

// User-scoped GET endpoints must NEVER be cached: responses are keyed by URL
// only (the JWT is not part of the cache key) and logout does not clear the
// cache, so caching them would leak one user's data to the next user on a
// shared device. Keep this list in sync with any new per-user endpoint.
const isUserDataPath = (pathname) =>
  pathname.startsWith('/api/v1/auth/') ||
  pathname.startsWith('/api/v1/users/') ||
  pathname.startsWith('/api/v1/notifications/') ||
  pathname.startsWith('/api/v1/my-contributions/') ||
  pathname.startsWith('/api/v1/contributions/') ||
  pathname.startsWith('/api/v1/route-progress/') ||
  pathname.startsWith('/api/v1/point-transactions/') ||
  pathname.startsWith('/api/v1/user-badges/')

const contributionSyncQueue = new BackgroundSyncPlugin('contributionsQueue', {
  maxRetentionTime: 24 * 60, // minutes (24 hours)
})

// Offline queue for contribution creation
registerRoute(
  ({ request, url }) =>
    request.method === 'POST' && url.pathname.startsWith('/api/v1/contributions/'),
  new NetworkOnly({
    plugins: [contributionSyncQueue],
  }),
)

// User data: Network Only (never cached — see isUserDataPath)
registerRoute(
  ({ request, url }) => request.method === 'GET' && isUserDataPath(url.pathname),
  new NetworkOnly(),
)

// Public API responses (GET): NetworkFirst so fresh data (e.g. after a
// moderation state transition) is shown whenever the network is reachable,
// falling back to cache only when offline. A short network timeout keeps the
// offline fallback snappy. Status 0 (opaque) responses are intentionally NOT
// cacheable here — same-origin API responses are never opaque.
registerRoute(
  ({ request, url }) =>
    request.method === 'GET' &&
    url.pathname.startsWith('/api/v1/') &&
    !isUserDataPath(url.pathname),
  new NetworkFirst({
    cacheName: 'api-v1',
    networkTimeoutSeconds: 5,
    plugins: [
      new CacheableResponsePlugin({ statuses: [200] }),
      new ExpirationPlugin({ maxAgeSeconds: 60 * 60 * 24, maxEntries: 500 }), // 24 hours
    ],
  }),
)

// Map tiles: Cache First (30 days). MUST be registered BEFORE the generic
// image route below — Workbox matches routes in registration order (first
// match wins), and OSM tiles also have request.destination === 'image', so a
// generic-image-first ordering would shadow this route. Opaque (status 0)
// responses are excluded so a captive-portal/error tile isn't cached as "good".
registerRoute(
  ({ request, url }) =>
    request.destination === 'image' &&
    (url.hostname === 'tile.openstreetmap.org' || url.hostname.endsWith('.tile.openstreetmap.org')),
  new CacheFirst({
    cacheName: 'map-tiles-osm',
    plugins: [
      new CacheableResponsePlugin({ statuses: [200] }),
      new ExpirationPlugin({ maxAgeSeconds: 60 * 60 * 24 * 30, maxEntries: 2000 }),
    ],
  }),
)

// Images / media: Cache First (7 days). Opaque responses excluded to avoid
// caching a broken cross-origin asset for the full TTL.
registerRoute(
  ({ request, url }) => request.destination === 'image' || url.pathname.startsWith('/media/'),
  new CacheFirst({
    cacheName: 'images-v1',
    plugins: [
      new CacheableResponsePlugin({ statuses: [200] }),
      new ExpirationPlugin({ maxAgeSeconds: 60 * 60 * 24 * 7, maxEntries: 500 }),
    ],
  }),
)
