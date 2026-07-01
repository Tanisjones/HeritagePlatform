import { ref, type Ref } from 'vue'
import { extractApiError } from '@/utils/apiError'

/**
 * Collapses the `loading = true / error = null / try / catch / finally` block
 * that was hand-rolled in every Pinia store action and ~20 view load()s.
 *
 * Two entry points:
 *
 *   // 1. Standalone — owns its own refs (typical in a view's <script setup>):
 *   const { loading, error, run } = useAsyncAction()
 *   onMounted(() => run(() => api.get('/things/').then(r => (things.value = r.data))))
 *
 *   // 2. withLoading — drives refs you already own (typical in a store):
 *   async function fetchRoutes() {
 *     return withLoading(loading, error, async () => {
 *       routes.value = unwrapResults(await routeService.list())
 *     })
 *   }
 *
 * On error the message is derived via extractApiError (DRF-aware). By default
 * the error is swallowed (returns undefined) so callers can branch on the
 * `error` ref; pass `{ rethrow: true }` to propagate (stores that let views
 * catch use this).
 */
export interface WithLoadingOptions {
  /** Re-throw after setting the error ref (default false). */
  rethrow?: boolean
  /** Override the fallback message when the error can't be parsed. */
  fallback?: string
}

export async function withLoading<T>(
  loading: Ref<boolean>,
  error: Ref<string | null>,
  fn: () => Promise<T>,
  options: WithLoadingOptions = {},
): Promise<T | undefined> {
  loading.value = true
  error.value = null
  try {
    return await fn()
  } catch (err) {
    error.value = extractApiError(err, options.fallback)
    if (options.rethrow) throw err
    return undefined
  } finally {
    loading.value = false
  }
}

export function useAsyncAction(options: WithLoadingOptions = {}) {
  const loading = ref(false)
  const error = ref<string | null>(null)

  function run<T>(fn: () => Promise<T>, overrides: WithLoadingOptions = {}) {
    return withLoading(loading, error, fn, { ...options, ...overrides })
  }

  return { loading, error, run }
}
