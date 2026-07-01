import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { routeService } from '@/services/api'
import { withLoading } from '@/composables/useAsyncAction'
import { unwrapResults } from '@/utils/pagination'
import type { HeritageRoute, RouteAwards, RouteCreateData, RouteRating, UserRouteProgress } from '@/types/heritage'

export const useRoutesStore = defineStore('routes', () => {
  const routes = ref<HeritageRoute[]>([])
  const currentRoute = ref<HeritageRoute | null>(null)
  const myRoutes = ref<HeritageRoute[]>([])
  const activeRoutes = ref<HeritageRoute[]>([])
  const nearbyRoutes = ref<HeritageRoute[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  const publishedRoutes = computed(() => routes.value.filter((r) => r.status === 'published'))
  const draftRoutes = computed(() => myRoutes.value.filter((r) => r.status === 'draft'))

  // Every action shares the same loading/error refs via withLoading and re-throws
  // so views can still catch (rethrow: true). Because it re-throws, the success
  // path always yields T (never undefined), so we assert that for callers that
  // consume the return value. List responses go through the shared unwrapResults
  // (handles both DRF `{results}` envelopes and bare arrays).
  const run = <T>(fn: () => Promise<T>) =>
    withLoading(loading, error, fn, { rethrow: true }) as Promise<T>

  async function fetchRoutes(params?: Record<string, any>) {
    await run(async () => {
      const res = await routeService.list(params)
      routes.value = unwrapResults<HeritageRoute>(res.data)
    })
  }

  async function fetchRoute(id: string) {
    return run(async () => {
      const res = await routeService.get(id)
      currentRoute.value = res.data as HeritageRoute
      return currentRoute.value
    })
  }

  async function createRoute(payload: RouteCreateData) {
    return run(async () => {
      const res = await routeService.create(payload)
      const created = res.data as HeritageRoute
      currentRoute.value = created
      myRoutes.value = [created, ...myRoutes.value]
      return created
    })
  }

  async function updateRoute(id: string, payload: Partial<RouteCreateData>) {
    return run(async () => {
      const res = await routeService.update(id, payload)
      const updated = res.data as HeritageRoute
      currentRoute.value = updated
      myRoutes.value = myRoutes.value.map((r) => (r.id === id ? updated : r))
      routes.value = routes.value.map((r) => (r.id === id ? updated : r))
      activeRoutes.value = activeRoutes.value.map((r) => (r.id === id ? updated : r))
      return updated
    })
  }

  async function deleteRoute(id: string) {
    await run(async () => {
      await routeService.delete(id)
      if (currentRoute.value?.id === id) currentRoute.value = null
      routes.value = routes.value.filter((r) => r.id !== id)
      myRoutes.value = myRoutes.value.filter((r) => r.id !== id)
      activeRoutes.value = activeRoutes.value.filter((r) => r.id !== id)
    })
  }

  async function fetchMyRoutes(params?: Record<string, any>) {
    await run(async () => {
      const res = await routeService.myRoutes(params)
      myRoutes.value = unwrapResults<HeritageRoute>(res.data)
    })
  }

  async function fetchActiveRoutes(params?: Record<string, any>) {
    await run(async () => {
      const res = await routeService.activeRoutes(params)
      activeRoutes.value = unwrapResults<HeritageRoute>(res.data)
    })
  }

  async function submitForReview(id: string) {
    await run(async () => {
      await routeService.submitForReview(id)
      if (currentRoute.value?.id === id) currentRoute.value.status = 'pending'
    })
  }

  async function startRoute(id: string) {
    return run(async () => {
      const res = await routeService.start(id)
      const progress = res.data as UserRouteProgress
      if (currentRoute.value?.id === id) currentRoute.value.user_progress = progress
      return progress
    })
  }

  async function checkInAtStop(
    routeId: string,
    stopId: string,
    coords?: { latitude: number; longitude: number },
  ) {
    return run(async () => {
      const res = await routeService.checkIn(routeId, { stop_id: stopId, ...(coords || {}) })
      const progress = res.data as UserRouteProgress
      if (currentRoute.value?.id === routeId) currentRoute.value.user_progress = progress
      return progress
    })
  }

  async function fetchNearbyRoutes(params: { latitude: number; longitude: number; radius?: number }) {
    return run(async () => {
      const res = await routeService.nearby(params)
      nearbyRoutes.value = unwrapResults<HeritageRoute>(res.data)
      return nearbyRoutes.value
    })
  }

  // Best-effort: a failed "similar routes" fetch shouldn't surface an error, so
  // this one stays outside withLoading and swallows.
  async function fetchSimilarRoutes(routeId: string) {
    try {
      const res = await routeService.similar(routeId)
      return unwrapResults<HeritageRoute>(res.data)
    } catch {
      return []
    }
  }

  async function archiveRoute(routeId: string) {
    await run(async () => {
      await routeService.archive(routeId)
      if (currentRoute.value?.id === routeId) currentRoute.value.status = 'archived'
      myRoutes.value = myRoutes.value.map((r) =>
        r.id === routeId ? { ...r, status: 'archived' } : r,
      )
    })
  }

  async function skipStop(routeId: string, stopId: string) {
    return run(async () => {
      const res = await routeService.skipStop(routeId, { stop_id: stopId })
      const progress = res.data as UserRouteProgress
      if (currentRoute.value?.id === routeId) currentRoute.value.user_progress = progress
      return progress
    })
  }

  async function completeRoute(routeId: string) {
    return run(async () => {
      const res = await routeService.complete(routeId)
      // The response is the progress object plus an `awards` block the backend
      // computed from the points/badges it just granted (exact, not a heuristic).
      const { awards, ...progress } = (res.data || {}) as UserRouteProgress & {
        awards?: RouteAwards
      }
      if (currentRoute.value?.id === routeId) {
        currentRoute.value.user_progress = progress as UserRouteProgress
        currentRoute.value.completion_count = (currentRoute.value.completion_count || 0) + 1
      }
      return { progress: progress as UserRouteProgress, awards: awards ?? { points: 0, badges: [] } }
    })
  }

  async function rateRoute(routeId: string, payload: { rating: number; comment?: string }) {
    return run(async () => {
      const res = await routeService.rate(routeId, payload)
      const rating = res.data as RouteRating
      if (currentRoute.value?.id === routeId) currentRoute.value.user_rating = rating
      return rating
    })
  }

  return {
    routes,
    currentRoute,
    myRoutes,
    activeRoutes,
    nearbyRoutes,
    loading,
    error,
    publishedRoutes,
    draftRoutes,
    fetchRoutes,
    fetchRoute,
    createRoute,
    updateRoute,
    deleteRoute,
    archiveRoute,
    fetchMyRoutes,
    fetchActiveRoutes,
    fetchNearbyRoutes,
    fetchSimilarRoutes,
    submitForReview,
    startRoute,
    checkInAtStop,
    skipStop,
    completeRoute,
    rateRoute,
  }
})
