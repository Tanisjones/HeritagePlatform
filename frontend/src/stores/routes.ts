import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { routeService } from '@/services/api'
import type { HeritageRoute, RouteCreateData, RouteRating, UserRouteProgress } from '@/types/heritage'

function unwrapResults<T>(data: any): T[] {
  if (!data) return []
  if (Array.isArray(data)) return data as T[]
  if (Array.isArray(data.results)) return data.results as T[]
  return []
}

export const useRoutesStore = defineStore('routes', () => {
  const routes = ref<HeritageRoute[]>([])
  const currentRoute = ref<HeritageRoute | null>(null)
  const myRoutes = ref<HeritageRoute[]>([])
  const activeRoutes = ref<HeritageRoute[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  const publishedRoutes = computed(() => routes.value.filter((r) => r.status === 'published'))
  const draftRoutes = computed(() => myRoutes.value.filter((r) => r.status === 'draft'))

  async function fetchRoutes(params?: Record<string, any>) {
    loading.value = true
    error.value = null
    try {
      const res = await routeService.list(params)
      routes.value = unwrapResults<HeritageRoute>(res.data)
    } catch (e: any) {
      error.value = e?.message || 'Failed to load routes'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function fetchRoute(id: string) {
    loading.value = true
    error.value = null
    try {
      const res = await routeService.get(id)
      currentRoute.value = res.data as HeritageRoute
      return currentRoute.value
    } catch (e: any) {
      error.value = e?.message || 'Failed to load route'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function createRoute(payload: RouteCreateData) {
    loading.value = true
    error.value = null
    try {
      const res = await routeService.create(payload)
      const created = res.data as HeritageRoute
      currentRoute.value = created
      myRoutes.value = [created, ...myRoutes.value]
      return created
    } catch (e: any) {
      error.value = e?.message || 'Failed to create route'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function updateRoute(id: string, payload: Partial<RouteCreateData>) {
    loading.value = true
    error.value = null
    try {
      const res = await routeService.update(id, payload)
      const updated = res.data as HeritageRoute
      currentRoute.value = updated
      myRoutes.value = myRoutes.value.map((r) => (r.id === id ? updated : r))
      routes.value = routes.value.map((r) => (r.id === id ? updated : r))
      activeRoutes.value = activeRoutes.value.map((r) => (r.id === id ? updated : r))
      return updated
    } catch (e: any) {
      error.value = e?.message || 'Failed to update route'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function deleteRoute(id: string) {
    loading.value = true
    error.value = null
    try {
      await routeService.delete(id)
      if (currentRoute.value?.id === id) currentRoute.value = null
      routes.value = routes.value.filter((r) => r.id !== id)
      myRoutes.value = myRoutes.value.filter((r) => r.id !== id)
      activeRoutes.value = activeRoutes.value.filter((r) => r.id !== id)
    } catch (e: any) {
      error.value = e?.message || 'Failed to delete route'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function fetchMyRoutes(params?: Record<string, any>) {
    loading.value = true
    error.value = null
    try {
      const res = await routeService.myRoutes(params)
      myRoutes.value = unwrapResults<HeritageRoute>(res.data)
    } catch (e: any) {
      error.value = e?.message || 'Failed to load my routes'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function fetchActiveRoutes(params?: Record<string, any>) {
    loading.value = true
    error.value = null
    try {
      const res = await routeService.activeRoutes(params)
      activeRoutes.value = unwrapResults<HeritageRoute>(res.data)
    } catch (e: any) {
      error.value = e?.message || 'Failed to load active routes'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function submitForReview(id: string) {
    loading.value = true
    error.value = null
    try {
      await routeService.submitForReview(id)
      if (currentRoute.value?.id === id) currentRoute.value.status = 'pending'
    } catch (e: any) {
      error.value = e?.message || 'Failed to submit route'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function startRoute(id: string) {
    loading.value = true
    error.value = null
    try {
      const res = await routeService.start(id)
      const progress = res.data as UserRouteProgress
      if (currentRoute.value?.id === id) currentRoute.value.user_progress = progress
      return progress
    } catch (e: any) {
      error.value = e?.message || 'Failed to start route'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function checkInAtStop(routeId: string, stopId: string) {
    loading.value = true
    error.value = null
    try {
      const res = await routeService.checkIn(routeId, { stop_id: stopId })
      const progress = res.data as UserRouteProgress
      if (currentRoute.value?.id === routeId) currentRoute.value.user_progress = progress
      return progress
    } catch (e: any) {
      error.value = e?.message || 'Failed to check in'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function skipStop(routeId: string, stopId: string) {
    loading.value = true
    error.value = null
    try {
      const res = await routeService.skipStop(routeId, { stop_id: stopId })
      const progress = res.data as UserRouteProgress
      if (currentRoute.value?.id === routeId) currentRoute.value.user_progress = progress
      return progress
    } catch (e: any) {
      error.value = e?.message || 'Failed to skip stop'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function completeRoute(routeId: string) {
    loading.value = true
    error.value = null
    try {
      const res = await routeService.complete(routeId)
      const progress = res.data as UserRouteProgress
      if (currentRoute.value?.id === routeId) {
        currentRoute.value.user_progress = progress
        currentRoute.value.completion_count = (currentRoute.value.completion_count || 0) + 1
      }
      return progress
    } catch (e: any) {
      error.value = e?.message || 'Failed to complete route'
      throw e
    } finally {
      loading.value = false
    }
  }

  async function rateRoute(routeId: string, payload: { rating: number; comment?: string }) {
    loading.value = true
    error.value = null
    try {
      const res = await routeService.rate(routeId, payload)
      const rating = res.data as RouteRating
      if (currentRoute.value?.id === routeId) currentRoute.value.user_rating = rating
      return rating
    } catch (e: any) {
      error.value = e?.message || 'Failed to rate route'
      throw e
    } finally {
      loading.value = false
    }
  }

  return {
    routes,
    currentRoute,
    myRoutes,
    activeRoutes,
    loading,
    error,
    publishedRoutes,
    draftRoutes,
    fetchRoutes,
    fetchRoute,
    createRoute,
    updateRoute,
    deleteRoute,
    fetchMyRoutes,
    fetchActiveRoutes,
    submitForReview,
    startRoute,
    checkInAtStop,
    skipStop,
    completeRoute,
    rateRoute,
  }
})

