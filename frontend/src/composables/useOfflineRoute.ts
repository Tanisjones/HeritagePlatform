import { ref } from 'vue'
import { apiBaseUrl } from '@/utils/apiUrl'
import { boundingBox, lngLatToTile, type LngLat } from '@/utils/geo'
import type { HeritageRoute } from '@/types/heritage'

/**
 * "Full offline route mode": proactively warm the browser/service-worker caches
 * for a route so it works with no coverage in the field. It fetches the route
 * detail JSON, every OSM tile covering the route's bounding box across a capped
 * zoom range, and each stop's images + audio. Everything lands in the caches the
 * existing service worker already manages (map-tiles-osm, images-v1, api-v1), so
 * no new cache strategy is needed — this is a client-driven pre-fetch.
 *
 * An index of downloaded routes is kept in localStorage so the UI can show what
 * is available offline.
 */

const OFFLINE_INDEX_KEY = 'offlineRoutes'
// Zoom band tuned for a walkable city route. Higher zooms explode tile counts.
const MIN_ZOOM = 13
const MAX_ZOOM = 16
const TILE_CONCURRENCY = 6
// Guard against accidentally trying to download a whole country.
const MAX_TILES = 1500

type OfflineIndex = Record<string, { title: string; tiles: number; savedAt: number }>

function readIndex(): OfflineIndex {
  try {
    return JSON.parse(localStorage.getItem(OFFLINE_INDEX_KEY) || '{}')
  } catch {
    return {}
  }
}

function writeIndex(index: OfflineIndex) {
  localStorage.setItem(OFFLINE_INDEX_KEY, JSON.stringify(index))
}

function routePoints(route: HeritageRoute): LngLat[] {
  const points: LngLat[] = []
  const path = route.path as any
  if (path && Array.isArray(path.coordinates)) {
    for (const c of path.coordinates) {
      if (Array.isArray(c) && c.length === 2) points.push([c[0], c[1]])
    }
  }
  for (const stop of route.stops || []) {
    const c = stop.heritage_item?.location?.coordinates
    if (c && c.length === 2) points.push([c[0], c[1]])
  }
  return points
}

/** Enumerate OSM tile URLs covering the points across the zoom band. */
export function tileUrlsForRoute(route: HeritageRoute): string[] {
  const points = routePoints(route)
  const bbox = boundingBox(points)
  if (!bbox) return []
  const [minLng, minLat, maxLng, maxLat] = bbox
  const urls: string[] = []
  for (let z = MIN_ZOOM; z <= MAX_ZOOM; z++) {
    const tl = lngLatToTile(minLng, maxLat, z) // top-left
    const br = lngLatToTile(maxLng, minLat, z) // bottom-right
    for (let x = tl.x; x <= br.x; x++) {
      for (let y = tl.y; y <= br.y; y++) {
        urls.push(`https://tile.openstreetmap.org/${z}/${x}/${y}.png`)
        if (urls.length >= MAX_TILES) return urls
      }
    }
  }
  return urls
}

function mediaUrlsForRoute(route: HeritageRoute): string[] {
  const urls: string[] = []
  for (const stop of route.stops || []) {
    const item = stop.heritage_item
    if (item?.primary_image) urls.push(item.primary_image)
    if (stop.audio_url) urls.push(stop.audio_url)
  }
  return urls
}

export function useOfflineRoute() {
  const downloading = ref(false)
  const progress = ref(0)
  const total = ref(0)
  const index = ref<OfflineIndex>(readIndex())

  function isSaved(routeId: string): boolean {
    return !!index.value[routeId]
  }

  function estimateTileCount(route: HeritageRoute): number {
    return tileUrlsForRoute(route).length
  }

  async function fetchAll(urls: string[]) {
    let i = 0
    async function worker() {
      while (i < urls.length) {
        const url = urls[i++]
        if (!url) continue
        try {
          // Default (cors) mode: OSM tiles + media send permissive CORS headers,
          // so the response is a real status-200 the service worker will cache.
          // (mode:'no-cors' would yield an opaque status-0 response that Workbox's
          // CacheableResponsePlugin({statuses:[200]}) refuses to store.)
          await fetch(url)
        } catch {
          /* best-effort warm-up */
        }
        progress.value++
      }
    }
    await Promise.all(Array.from({ length: TILE_CONCURRENCY }, worker))
  }

  async function downloadRouteForOffline(route: HeritageRoute) {
    if (downloading.value) return
    downloading.value = true
    progress.value = 0

    const tileUrls = tileUrlsForRoute(route)
    const mediaUrls = mediaUrlsForRoute(route)
    const base = apiBaseUrl().replace(/\/$/, '')
    const detailUrl = `${base}/routes/${route.id}/`
    total.value = tileUrls.length + mediaUrls.length + 1

    try {
      // Route detail JSON (lands in the api-v1 NetworkFirst cache).
      try {
        await fetch(detailUrl)
      } catch {
        /* ignore */
      }
      progress.value++
      await fetchAll([...tileUrls, ...mediaUrls])

      index.value = { ...index.value, [route.id]: { title: route.title, tiles: tileUrls.length, savedAt: Date.now() } }
      writeIndex(index.value)
    } finally {
      downloading.value = false
    }
  }

  async function removeOfflineRoute(routeId: string) {
    // Drop the index entry. Cached tiles/media are shared and expire on their
    // own; we clear the api entry for this route where possible.
    const next = { ...index.value }
    delete next[routeId]
    index.value = next
    writeIndex(next)
    try {
      const cache = await caches.open('api-v1')
      const base = apiBaseUrl().replace(/\/$/, '')
      await cache.delete(`${base}/routes/${routeId}/`)
    } catch {
      /* ignore */
    }
  }

  return {
    downloading,
    progress,
    total,
    index,
    isSaved,
    estimateTileCount,
    downloadRouteForOffline,
    removeOfflineRoute,
  }
}
