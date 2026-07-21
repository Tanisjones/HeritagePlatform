import type { RouteRecordRaw } from 'vue-router'
import { CITY_STORAGE_KEY, ALL_CITIES } from '@/services/api'

/**
 * City URL context — the single place that knows how an internal city slug
 * maps to a URL segment and back.
 *
 * Public content lives under `/:citySlug/...`; the pseudo-slug `all` maps to
 * the internal ALL_CITIES sentinel (no X-City header). Account/management
 * pages stay unprefixed and keep using the persisted slug.
 */

/** URL segment standing for the cross-city ("all cities") mode. */
export const ALL_SEGMENT = 'all'

/** Internal slug (or the ALL_CITIES sentinel) → URL segment. */
export function segmentForSlug(slug: string | null | undefined): string {
  if (!slug || slug === ALL_CITIES) return ALL_SEGMENT
  return slug
}

/** URL segment → internal slug (or the ALL_CITIES sentinel). */
export function slugForSegment(segment: string): string {
  return segment === ALL_SEGMENT ? ALL_CITIES : segment
}

/**
 * Swap the leading city segment of a rooted path for another city, keeping
 * the rest of the path. Takes a *path* only — query and hash are not part of
 * it and must be preserved by the caller.
 */
export function swapCitySegment(path: string, segment: string): string {
  return `/${segment}${path.replace(/^\/[^/]+/, '')}`
}

/** URL segment for the persisted city context ('all' when none/sentinel). */
export function activeContextSegment(): string {
  let stored: string | null = null
  try {
    stored = localStorage.getItem(CITY_STORAGE_KEY)
  } catch {
    // localStorage unavailable (privacy mode): fall through to 'all'.
  }
  return segmentForSlug(stored)
}

/**
 * Unprefixed content paths kept alive as redirects (old bookmarks, stray
 * pushes). Derived from the city shell's own children rather than
 * hand-maintained, so a new city-scoped route cannot silently ship without
 * its legacy redirect.
 */
export function legacyPathsFrom(children: readonly { path: string }[]): string[] {
  return children.map((child) => `/${child.path}`).filter((path) => path !== '/')
}

/**
 * Redirect records for the legacy paths. `to.path` is the concrete URL, so a
 * single generic redirect covers the param'd paths too. Static first segments
 * always outrank `/:citySlug` in vue-router's scoring, so these can sit at the
 * same level as the city shell.
 */
export function makeLegacyRedirects(paths: readonly string[]): RouteRecordRaw[] {
  return paths.map((path) => ({
    path,
    redirect: (to) => ({
      path: `/${activeContextSegment()}${to.path}`,
      query: to.query,
      hash: to.hash,
    }),
  }))
}
