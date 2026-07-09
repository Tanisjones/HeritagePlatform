import { computed, ref } from 'vue'
import { useGeolocation as vueUseGeolocation } from '@vueuse/core'
import type { LngLat } from '@/utils/geo'

/**
 * Thin wrapper over @vueuse/core's useGeolocation, exposing a route-navigation
 * friendly surface: a `[lng, lat]` tuple, accuracy, an availability flag, and
 * pause/resume so the watch can be toggled with a "follow me" control.
 */
export function useGeolocation() {
  const enabled = ref(false)
  const { coords, locatedAt, error, resume, pause, isSupported } = vueUseGeolocation({
    enableHighAccuracy: true,
    immediate: false,
  })

  // GeoJSON order [lng, lat]; null until we have a real fix.
  const lngLat = computed<LngLat | null>(() => {
    const lat = coords.value?.latitude
    const lng = coords.value?.longitude
    if (
      typeof lat !== 'number' ||
      typeof lng !== 'number' ||
      !Number.isFinite(lat) ||
      !Number.isFinite(lng)
    ) {
      return null
    }
    return [lng, lat]
  })

  const accuracy = computed(() => coords.value?.accuracy ?? null)

  function start() {
    enabled.value = true
    resume()
  }

  function stop() {
    enabled.value = false
    pause()
  }

  /**
   * One-shot fix for "usar mi ubicación" buttons — resolves a single [lng, lat]
   * without engaging the continuous watch that start()/stop() manage.
   */
  function getCurrent(timeoutMs = 10000): Promise<LngLat> {
    return new Promise((resolve, reject) => {
      if (typeof navigator === 'undefined' || !navigator.geolocation) {
        reject(new Error('geolocation-unsupported'))
        return
      }
      navigator.geolocation.getCurrentPosition(
        (pos) => resolve([pos.coords.longitude, pos.coords.latitude]),
        (err) => reject(err),
        { enableHighAccuracy: true, timeout: timeoutMs, maximumAge: 30000 },
      )
    })
  }

  return { enabled, lngLat, accuracy, locatedAt, error, isSupported, start, stop, getCurrent }
}
