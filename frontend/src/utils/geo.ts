/**
 * Lightweight client-side geo helpers for route navigation (proximity
 * auto-check-in, offline bbox). Coordinates are GeoJSON `[lng, lat]` pairs.
 */

const EARTH_RADIUS_M = 6_371_000

export type LngLat = [number, number]

/** Great-circle distance in metres between two `[lng, lat]` points. */
export function haversineMeters(a: LngLat, b: LngLat): number {
  const [lng1, lat1] = a
  const [lng2, lat2] = b
  const toRad = (d: number) => (d * Math.PI) / 180
  const dPhi = toRad(lat2 - lat1)
  const dLambda = toRad(lng2 - lng1)
  const h =
    Math.sin(dPhi / 2) ** 2 +
    Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLambda / 2) ** 2
  return 2 * EARTH_RADIUS_M * Math.asin(Math.min(1, Math.sqrt(h)))
}

/** Bounding box `[minLng, minLat, maxLng, maxLat]` of a set of `[lng, lat]` points. */
export function boundingBox(points: LngLat[]): [number, number, number, number] | null {
  if (!points.length) return null
  let minLng = Infinity
  let minLat = Infinity
  let maxLng = -Infinity
  let maxLat = -Infinity
  for (const [lng, lat] of points) {
    if (lng < minLng) minLng = lng
    if (lat < minLat) minLat = lat
    if (lng > maxLng) maxLng = lng
    if (lat > maxLat) maxLat = lat
  }
  return [minLng, minLat, maxLng, maxLat]
}

/** Slippy-map tile (x, y) covering `[lng, lat]` at a zoom level. */
export function lngLatToTile(lng: number, lat: number, zoom: number): { x: number; y: number } {
  const n = 2 ** zoom
  const x = Math.floor(((lng + 180) / 360) * n)
  const latRad = (lat * Math.PI) / 180
  const y = Math.floor(
    ((1 - Math.log(Math.tan(latRad) + 1 / Math.cos(latRad)) / Math.PI) / 2) * n,
  )
  return { x: Math.max(0, Math.min(n - 1, x)), y: Math.max(0, Math.min(n - 1, y)) }
}

// ── WKT / GeoJSON geometry parsing ───────────────────────────────────────────
// Backends emit locations either as a GeoJSON object or as a (possibly
// SRID-prefixed) WKT string. These helpers unify the three hand-rolled parsers
// that used to live in RouteMap, HomeView and ContributionReviewView. They
// return Leaflet order `[lat, lng]` since every consumer feeds Leaflet.

/** A Leaflet coordinate pair, `[lat, lng]`. */
export type LatLng = [number, number]

type GeoJsonGeometry = { type?: string; coordinates?: unknown }

/**
 * Parse a POINT from a WKT string ("SRID=4326;POINT (lng lat)" or
 * "POINT(lng lat)") or a GeoJSON Point object into `[lat, lng]`. Returns null
 * when the value is empty or unparseable.
 */
export function parsePoint(value: string | GeoJsonGeometry | null | undefined): LatLng | null {
  if (!value) return null

  if (typeof value === 'object') {
    const coords = value.coordinates
    if (Array.isArray(coords) && coords.length >= 2) {
      const lng = Number(coords[0])
      const lat = Number(coords[1])
      return Number.isFinite(lat) && Number.isFinite(lng) ? [lat, lng] : null
    }
    return null
  }

  // WKT string: only accept an actual POINT (anchored to the keyword so a
  // POLYGON/MULTIPOINT/LINESTRING isn't mis-parsed as its first vertex). The
  // number pattern tolerates a sign and scientific notation (e.g. "1.5e-3").
  const num = String.raw`[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?`
  const match = value.match(new RegExp(String.raw`POINT\s*\(\s*(${num})\s+(${num})\s*\)`, 'i'))
  if (!match) return null
  const lng = Number(match[1])
  const lat = Number(match[2])
  return Number.isFinite(lat) && Number.isFinite(lng) ? [lat, lng] : null
}

/**
 * Parse a LINESTRING from a WKT string ("SRID=4326;LINESTRING (lng lat, …)" or
 * "LINESTRING(lng lat, …)") or a GeoJSON LineString object into an array of
 * `[lat, lng]`. Returns null when empty or unparseable.
 */
export function parseLineString(
  value: string | GeoJsonGeometry | null | undefined,
): LatLng[] | null {
  if (!value) return null

  if (typeof value === 'object') {
    if (value.type === 'LineString' && Array.isArray(value.coordinates)) {
      const points = (value.coordinates as unknown[])
        .map((c): LatLng | null => {
          const pair = c as unknown[]
          const lng = Number(pair?.[0])
          const lat = Number(pair?.[1])
          return Number.isFinite(lat) && Number.isFinite(lng) ? [lat, lng] : null
        })
        .filter((p): p is LatLng => p !== null)
      return points.length ? points : null
    }
    return null
  }

  const match = value.match(/LINESTRING\s*\(\s*([^)]+)\s*\)/i)
  if (!match || !match[1]) return null
  const points: LatLng[] = []
  for (const pair of match[1].split(',')) {
    const [lngStr, latStr] = pair.trim().split(/\s+/).filter(Boolean)
    const lng = Number(lngStr)
    const lat = Number(latStr)
    if (Number.isFinite(lat) && Number.isFinite(lng)) points.push([lat, lng])
  }
  return points.length ? points : null
}
