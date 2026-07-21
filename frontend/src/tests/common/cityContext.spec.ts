import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { RouteLocation } from 'vue-router'

// Same deterministic in-memory Storage the city-store spec uses.
const backing = new Map<string, string>()
vi.stubGlobal('localStorage', {
  getItem: (key: string) => backing.get(key) ?? null,
  setItem: (key: string, value: string) => void backing.set(key, String(value)),
  removeItem: (key: string) => void backing.delete(key),
  clear: () => backing.clear(),
})

vi.mock('@/services/api', () => ({
  CITY_STORAGE_KEY: 'hp_city',
  ALL_CITIES: '__all__',
}))

import {
  ALL_SEGMENT,
  activeContextSegment,
  legacyPathsFrom,
  makeLegacyRedirects,
  segmentForSlug,
  slugForSegment,
  swapCitySegment,
} from '@/router/cityContext'

/** Stand-in for the city shell's `children` array (only `path` matters here). */
const CITY_CHILDREN = [
  { path: '' },
  { path: 'explore' },
  { path: 'routes/:id' },
  { path: 'learn/plans/:id/class' },
]

function resolveRedirect(path: string, to: Partial<RouteLocation>) {
  const paths = legacyPathsFrom(CITY_CHILDREN)
  const record = makeLegacyRedirects(paths).find((r) => r.path === path)
  expect(record, `no legacy record for ${path}`).toBeDefined()
  const redirect = record!.redirect as (to: RouteLocation) => {
    path: string
    query: unknown
    hash: string
  }
  return redirect({ query: {}, hash: '', ...to } as RouteLocation)
}

describe('segment mapping', () => {
  it('maps the all-cities sentinel to the public segment and back', () => {
    expect(segmentForSlug('__all__')).toBe(ALL_SEGMENT)
    expect(slugForSegment(ALL_SEGMENT)).toBe('__all__')
  })

  it('passes concrete slugs through unchanged', () => {
    expect(segmentForSlug('tarragona')).toBe('tarragona')
    expect(slugForSegment('tarragona')).toBe('tarragona')
  })

  it("treats an absent slug as the 'all' segment", () => {
    expect(segmentForSlug(null)).toBe(ALL_SEGMENT)
    expect(segmentForSlug(undefined)).toBe(ALL_SEGMENT)
    expect(segmentForSlug('')).toBe(ALL_SEGMENT)
  })
})

describe('swapCitySegment', () => {
  it('replaces the leading city segment and keeps the rest of the path', () => {
    expect(swapCitySegment('/riobamba/explore', 'tarragona')).toBe('/tarragona/explore')
    expect(swapCitySegment('/riobamba/learn/plans/7/class', 'all')).toBe(
      '/all/learn/plans/7/class',
    )
  })

  it('handles a bare city landing', () => {
    expect(swapCitySegment('/riobamba', 'tarragona')).toBe('/tarragona')
  })
})

describe('activeContextSegment', () => {
  beforeEach(() => localStorage.clear())

  it("falls back to 'all' when nothing is persisted", () => {
    expect(activeContextSegment()).toBe('all')
  })

  it("maps the all-cities sentinel to the 'all' URL segment", () => {
    localStorage.setItem('hp_city', '__all__')
    expect(activeContextSegment()).toBe('all')
  })

  it('returns the persisted city slug', () => {
    localStorage.setItem('hp_city', 'tarragona')
    expect(activeContextSegment()).toBe('tarragona')
  })
})

describe('legacyPathsFrom', () => {
  it("roots every child path and drops the city landing (there is no legacy '/')", () => {
    expect(legacyPathsFrom(CITY_CHILDREN)).toEqual([
      '/explore',
      '/routes/:id',
      '/learn/plans/:id/class',
    ])
  })

  it('derives a redirect for every city-scoped route, so the two cannot drift', () => {
    const paths = legacyPathsFrom(CITY_CHILDREN)
    expect(makeLegacyRedirects(paths).map((r) => r.path)).toEqual(paths)
  })
})

describe('makeLegacyRedirects', () => {
  beforeEach(() => localStorage.clear())

  it('prefixes a plain path with the persisted city and keeps query/hash', () => {
    localStorage.setItem('hp_city', 'tarragona')
    const target = resolveRedirect('/explore', {
      path: '/explore',
      query: { search: 'anfiteatro' },
      hash: '#map',
    })
    expect(target).toEqual({
      path: '/tarragona/explore',
      query: { search: 'anfiteatro' },
      hash: '#map',
    })
  })

  it("sends param'd paths to /all when nothing is persisted", () => {
    const target = resolveRedirect('/routes/:id', { path: '/routes/42' })
    expect(target.path).toBe('/all/routes/42')
  })
})
