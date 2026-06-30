import api from '@/services/api'

/**
 * Helpers for deriving API/backend URLs from the env-driven base.
 *
 * The API base comes from `VITE_API_BASE_URL` (e.g. `http://localhost:8000/api/v1`
 * in dev, or a relative `/api/v1` in production). These helpers centralise the
 * logic so it is not re-derived (divergently) in every component.
 */

/** The configured API base URL, e.g. `http://localhost:8000/api/v1` or `/api/v1`. */
export function apiBaseUrl(): string {
  return String(api.defaults?.baseURL || import.meta.env.VITE_API_BASE_URL || '')
}

/**
 * Origin of the backend that serves `/media/...` assets, derived from the API base.
 *
 * In production the base is relative (`/api/v1`), so there is no explicit origin
 * and this returns `''` — media is then fetched as a same-origin relative path
 * served by nginx. In dev the base is absolute, so this returns its origin
 * (e.g. `http://localhost:8000`). Parsing as a URL (rather than stripping a
 * trailing `/api/v1` by regex) handles non-canonical bases robustly.
 */
export function backendOrigin(): string {
  const base = apiBaseUrl()
  if (!base) return ''
  try {
    // Absolute base → real origin. Relative base → resolves to the page origin,
    // which we treat as same-origin and represent as '' (relative media paths).
    const url = new URL(base, window.location.origin)
    return url.origin === window.location.origin ? '' : url.origin
  } catch {
    return ''
  }
}

/**
 * Resolve a possibly-relative media URL to an absolute one (or leave absolute
 * URLs untouched). `/media/...` paths are prefixed with the backend origin.
 */
export function resolveMediaUrl(url: string | null | undefined): string {
  if (!url) return ''
  if (url.startsWith('http')) return url
  if (url.startsWith('/media')) return `${backendOrigin()}${url}`
  return url
}
