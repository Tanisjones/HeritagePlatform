import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

// The store persists the active slug; give the environment a deterministic
// in-memory Storage regardless of what the DOM shim provides.
const backing = new Map<string, string>()
vi.stubGlobal('localStorage', {
  getItem: (key: string) => backing.get(key) ?? null,
  setItem: (key: string, value: string) => void backing.set(key, String(value)),
  removeItem: (key: string) => void backing.delete(key),
  clear: () => backing.clear(),
})

const listMock = vi.fn()
vi.mock('@/services/api', () => ({
  cityService: { list: (...args: unknown[]) => listMock(...args) },
  CITY_STORAGE_KEY: 'hp_city',
}))

import { useCityStore } from '@/stores/city'

const CITIES = [
  {
    id: 1, slug: 'riobamba', name: 'Riobamba', country: 'EC', country_name: 'Ecuador',
    timezone: 'America/Guayaquil', center: { type: 'Point', coordinates: [-78.6479, -1.6735] },
    default_zoom: 13, default_language: 'es', is_active: true,
  },
  {
    id: 2, slug: 'cuenca', name: 'Cuenca', country: 'EC', country_name: 'Ecuador',
    timezone: 'America/Guayaquil', center: { type: 'Point', coordinates: [-79.0045, -2.9006] },
    default_zoom: 14, default_language: 'es', is_active: true,
  },
]

describe('city store', () => {
  beforeEach(() => {
    localStorage.clear()
    setActivePinia(createPinia())
    listMock.mockReset()
  })

  it('loads cities and persists the first as active when nothing is stored', async () => {
    listMock.mockResolvedValue({ data: CITIES })
    const store = useCityStore()
    await store.load()
    expect(store.cities).toHaveLength(2)
    expect(store.activeCity?.slug).toBe('riobamba')
    expect(localStorage.getItem('hp_city')).toBe('riobamba')
  })

  it('self-heals a stale persisted slug', async () => {
    localStorage.setItem('hp_city', 'ghost-town')
    listMock.mockResolvedValue({ data: CITIES })
    const store = useCityStore()
    await store.load()
    expect(store.activeCitySlug).toBe('riobamba')
    expect(localStorage.getItem('hp_city')).toBe('riobamba')
  })

  it('keeps a valid persisted slug and swaps GeoJSON lng/lat to Leaflet lat/lng', async () => {
    localStorage.setItem('hp_city', 'cuenca')
    listMock.mockResolvedValue({ data: CITIES })
    const store = useCityStore()
    await store.load()
    expect(store.activeCity?.slug).toBe('cuenca')
    expect(store.mapCenter).toEqual([-2.9006, -79.0045])
    expect(store.mapZoom).toBe(14)
  })

  it('survives a catalog fetch failure without touching the stored slug', async () => {
    localStorage.setItem('hp_city', 'cuenca')
    listMock.mockRejectedValue(new Error('offline'))
    const store = useCityStore()
    await store.load()
    expect(store.cities).toHaveLength(0)
    expect(localStorage.getItem('hp_city')).toBe('cuenca')
  })

  it('adoptSlug persists a deep-linked city without reloading', async () => {
    const store = useCityStore()
    store.adoptSlug('cuenca')
    expect(localStorage.getItem('hp_city')).toBe('cuenca')
    expect(store.activeCitySlug).toBe('cuenca')
  })
})
