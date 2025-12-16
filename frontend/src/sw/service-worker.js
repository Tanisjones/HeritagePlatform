/* eslint-disable no-restricted-globals */

import { cleanupOutdatedCaches, createHandlerBoundToURL, precacheAndRoute } from 'workbox-precaching'
import { BackgroundSyncPlugin } from 'workbox-background-sync'
import { registerRoute } from 'workbox-routing'
import { CacheFirst, NetworkFirst, NetworkOnly, StaleWhileRevalidate } from 'workbox-strategies'
import { CacheableResponsePlugin } from 'workbox-cacheable-response'
import { ExpirationPlugin } from 'workbox-expiration'

// Precache Vite build assets (app shell)
precacheAndRoute(self.__WB_MANIFEST)
cleanupOutdatedCaches()

// SPA navigation fallback to index.html
registerRoute(
  ({ request }) => request.mode === 'navigate',
  createHandlerBoundToURL('/index.html'),
)

const apiResourceParts = (pathname) => {
  const parts = pathname.split('/').filter(Boolean)
  const v1Index = parts.indexOf('v1')
  if (v1Index === -1) return null
  return parts.slice(v1Index + 1)
}

const isUserDataPath = (pathname) =>
  pathname.startsWith('/api/v1/auth/') ||
  pathname.startsWith('/api/v1/users/') ||
  pathname.startsWith('/api/v1/notifications/')

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

// User data: Network Only
registerRoute(
  ({ request, url }) => request.method === 'GET' && isUserDataPath(url.pathname),
  new NetworkOnly(),
)

// API responses (GET)
registerRoute(
  ({ request, url }) => request.method === 'GET' && url.pathname.startsWith('/api/v1/') && !isUserDataPath(url.pathname),
  async (options) => {
    const parts = apiResourceParts(options.url.pathname) ?? []

    // Heuristic:
    // - List endpoints: /api/v1/<resource>/ (resource parts length === 1)
    // - Detail endpoints: /api/v1/<resource>/<id>/ (resource parts length >= 2)
    const isListLike = parts.length <= 1 || options.url.searchParams.has('page')

    if (isListLike) {
      return new NetworkFirst({
        cacheName: 'api-list-v1',
        networkTimeoutSeconds: 5,
        plugins: [
          new CacheableResponsePlugin({ statuses: [0, 200] }),
          new ExpirationPlugin({ maxAgeSeconds: 60 * 60, maxEntries: 200 }), // 1 hour
        ],
      }).handle(options)
    }

    return new StaleWhileRevalidate({
      cacheName: 'api-detail-v1',
      plugins: [
        new CacheableResponsePlugin({ statuses: [0, 200] }),
        new ExpirationPlugin({ maxAgeSeconds: 60 * 60 * 24, maxEntries: 500 }), // 24 hours
      ],
    }).handle(options)
  },
)

// Images: Cache First (7 days)
registerRoute(
  ({ request, url }) => request.destination === 'image' || url.pathname.startsWith('/media/'),
  new CacheFirst({
    cacheName: 'images-v1',
    plugins: [
      new CacheableResponsePlugin({ statuses: [0, 200] }),
      new ExpirationPlugin({ maxAgeSeconds: 60 * 60 * 24 * 7, maxEntries: 500 }),
    ],
  }),
)

// Map tiles: Cache First (30 days)
registerRoute(
  ({ request, url }) =>
    request.destination === 'image' &&
    (url.hostname === 'tile.openstreetmap.org' || url.hostname.endsWith('.tile.openstreetmap.org')),
  new CacheFirst({
    cacheName: 'map-tiles-osm',
    plugins: [
      new CacheableResponsePlugin({ statuses: [0, 200] }),
      new ExpirationPlugin({ maxAgeSeconds: 60 * 60 * 24 * 30, maxEntries: 2000 }),
    ],
  }),
)
