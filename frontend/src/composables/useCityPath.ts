import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useCityStore } from '@/stores/city'
import { ALL_SEGMENT, segmentForSlug } from '@/router/cityContext'

/**
 * City-prefixed link builder. The route param wins (inside the city shell);
 * outside it (gateway, account pages) the persisted context is the fallback,
 * so content links from e.g. /dashboard land in the user's active city.
 */
export function useCityPath() {
  const route = useRoute()
  const cityStore = useCityStore()

  const citySegment = computed(() => {
    const param = route.params.citySlug
    if (typeof param === 'string' && param) {
      // A slug the catalog doesn't know (typo'd or stale link) would otherwise
      // propagate into every link on the 404 page. Only override once the
      // catalog is loaded — offline, trust the URL.
      const unknown =
        param !== ALL_SEGMENT &&
        cityStore.loaded &&
        cityStore.cities.length > 0 &&
        !cityStore.cities.some((c) => c.slug === param)
      if (!unknown) return param
    }
    return segmentForSlug(cityStore.activeCitySlug)
  })

  const cityPath = (path = '') => `/${citySegment.value}${path}`

  /**
   * Link to content that belongs to a *specific* city (a record carrying its
   * own `city`), rather than to the browsing context. Falls back to the
   * current context when the record has no city attached.
   */
  const cityPathFor = (slug: string | null | undefined, path = '') =>
    `/${slug || citySegment.value}${path}`

  return { citySegment, cityPath, cityPathFor }
}
