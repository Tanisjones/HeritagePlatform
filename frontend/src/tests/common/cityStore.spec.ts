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
const setRequestCityMock = vi.fn()
vi.mock('@/services/api', () => ({
  cityService: { list: (...args: unknown[]) => listMock(...args) },
  setRequestCity: (...args: unknown[]) => setRequestCityMock(...args),
  CITY_STORAGE_KEY: 'hp_city',
  ALL_CITIES: '__all__',
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

  it('shares one request between concurrent callers', async () => {
    // App.vue, CityShellView and GatewayView all call load() on first paint,
    // and `loaded` only flips after the await — without a shared in-flight
    // promise that is three identical GET /cities/ on every cold load.
    listMock.mockResolvedValue({ data: CITIES })
    const store = useCityStore()
    await Promise.all([store.load(), store.load(), store.load()])
    expect(listMock).toHaveBeenCalledTimes(1)
  })

  it('records a catalog failure so callers can offer a retry', async () => {
    listMock.mockRejectedValue(new Error('offline'))
    const store = useCityStore()
    await store.load()
    expect(store.loaded).toBe(false)
    expect(store.loadError).toBe(true)
    // A failed load must stay retryable — the gateway is the app's front door.
    listMock.mockResolvedValue({ data: CITIES })
    await store.load()
    expect(store.loaded).toBe(true)
    expect(store.loadError).toBe(false)
    expect(listMock).toHaveBeenCalledTimes(2)
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

  it('adoptSlug scopes this tab to the URL city WITHOUT persisting it', async () => {
    // Browsing a city is not choosing one. hp_city is shared by every tab, so
    // writing it here would let two tabs on two cities overwrite each other's
    // scope, and would silently re-point the account pages of anyone who
    // follows a cross-city link.
    localStorage.setItem('hp_city', 'riobamba')
    setActivePinia(createPinia())
    const store = useCityStore()
    await store.adoptSlug('cuenca')
    expect(store.activeCitySlug).toBe('cuenca')
    expect(localStorage.getItem('hp_city')).toBe('riobamba')
    expect(setRequestCityMock).toHaveBeenLastCalledWith('cuenca')
  })

  it('releases the URL city on leaving the shell, falling back to the chosen one', async () => {
    localStorage.setItem('hp_city', 'riobamba')
    setActivePinia(createPinia())
    const store = useCityStore()
    await store.adoptSlug('cuenca')
    store.releaseUrlCity()
    expect(store.activeCitySlug).toBe('riobamba')
    expect(setRequestCityMock).toHaveBeenLastCalledWith(null)
  })

  it('setCity persists the explicit choice', async () => {
    const store = useCityStore()
    const assign = vi.fn()
    vi.spyOn(window, 'location', 'get').mockReturnValue({
      pathname: '/moderation', search: '', hash: '', assign,
    } as unknown as Location)
    await store.setCity('cuenca')
    expect(localStorage.getItem('hp_city')).toBe('cuenca')
    // No targetPath → stay exactly where the user is (the old reload()
    // behaviour), so switching city on /moderation does not eject them.
    expect(assign).toHaveBeenCalledWith('/moderation')
    vi.restoreAllMocks()
  })

  it('treats the all-cities sentinel as known and unsets the active city (C1)', async () => {
    localStorage.setItem('hp_city', '__all__')
    listMock.mockResolvedValue({ data: CITIES })
    const store = useCityStore()
    await store.load()
    // Not "self-healed" away — the sentinel survives the catalog load…
    expect(store.activeCitySlug).toBe('__all__')
    expect(store.isAllCities).toBe(true)
    // …and no single city is active (views fall back to defaults).
    expect(store.activeCity).toBeNull()
    expect(store.switcherValue).toBe('__all__')
  })

})
