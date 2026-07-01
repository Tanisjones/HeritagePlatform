import { computed, ref, watch, type Ref } from 'vue'
import { useGeolocation } from '@/composables/useGeolocation'
import { haversineMeters, type LngLat } from '@/utils/geo'
import type { HeritageRoute, RouteStop } from '@/types/heritage'

// Auto check-in when the live position is within this many metres of the next
// stop. Deliberately tighter than the server's check-in radius so a drive-by
// doesn't trigger it.
const AUTO_CHECKIN_THRESHOLD_M = 40
// Don't auto-check-in on a low-quality fix: a jittery reading with a large
// accuracy radius can momentarily land within the threshold without the user
// actually being there.
const MAX_ACCURACY_M = 50

/**
 * On-the-ground navigation: tracks the user's position and auto-checks-in at the
 * next unvisited stop when they get close. The live position and any auto
 * check-in still go through the caller's `onCheckIn` (which forwards coords to
 * the backend). Manual check-in remains available; this is purely additive.
 */
export function useRouteNavigation(
  currentRoute: Ref<HeritageRoute | null>,
  onCheckIn: (stopId: string, coords: { latitude: number; longitude: number }) => Promise<unknown>,
) {
  const { enabled, lngLat, accuracy, isSupported, error, start, stop } = useGeolocation()
  const lastAutoStopId = ref<string | null>(null)

  const visitedIds = computed(
    () => new Set((currentRoute.value?.user_progress?.visited_stops || []).map((s) => s.id)),
  )

  const orderedStops = computed<RouteStop[]>(() =>
    (currentRoute.value?.stops || []).slice().sort((a, b) => a.order - b.order),
  )

  const nextStop = computed<RouteStop | null>(
    () => orderedStops.value.find((s) => !visitedIds.value.has(s.id)) || null,
  )

  function stopLngLat(s: RouteStop): LngLat | null {
    const c = s.heritage_item?.location?.coordinates
    if (!c || c.length !== 2) return null
    return [c[0], c[1]]
  }

  // Distance (m) from the live position to the next stop, if both are known.
  const distanceToNext = computed<number | null>(() => {
    const pos = lngLat.value
    const stopPos = nextStop.value ? stopLngLat(nextStop.value) : null
    if (!pos || !stopPos) return null
    return haversineMeters(pos, stopPos)
  })

  watch([lngLat, nextStop], async () => {
    if (!enabled.value) return
    const target = nextStop.value
    const dist = distanceToNext.value
    const pos = lngLat.value
    if (!target || dist === null || pos === null) return
    // Ignore low-quality fixes: a large accuracy radius means the reading could
    // be well outside the threshold even if the point lands inside it.
    if (accuracy.value !== null && accuracy.value > MAX_ACCURACY_M) return
    if (dist > AUTO_CHECKIN_THRESHOLD_M) return
    if (lastAutoStopId.value === target.id) return
    lastAutoStopId.value = target.id
    try {
      await onCheckIn(target.id, { latitude: pos[1], longitude: pos[0] })
    } catch {
      // Allow a later retry for this stop if the check-in failed.
      lastAutoStopId.value = null
    }
  })

  return {
    following: enabled,
    lngLat,
    accuracy,
    isSupported,
    error,
    nextStop,
    distanceToNext,
    startFollowing: start,
    stopFollowing: stop,
  }
}
