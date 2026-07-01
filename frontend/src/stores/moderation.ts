import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { curatorService } from '@/services/api'
import { withLoading } from '@/composables/useAsyncAction'
import { unwrapResults } from '@/utils/pagination'
import type { CuratorQueueItem, CuratorReviewDetail, CuratorStats } from '@/types/moderation'

export const useModerationStore = defineStore('moderation', () => {
  const queue = ref<CuratorQueueItem[]>([])
  const currentItem = ref<CuratorReviewDetail | null>(null)
  const stats = ref<CuratorStats | null>(null)
  const filters = ref<Record<string, any>>({ status: 'pending' })
  const loading = ref(false)
  const error = ref<string | null>(null)

  const isEmpty = computed(() => !loading.value && queue.value.length === 0)

  // Fetches swallow errors into the `error` ref (no rethrow) — views bind it.
  const run = <T>(fn: () => Promise<T>) => withLoading(loading, error, fn)

  async function fetchQueue(overrides?: Record<string, any>) {
    await run(async () => {
      const params = { ...filters.value, ...(overrides || {}) }
      const response = await curatorService.queue(params)
      queue.value = unwrapResults<CuratorQueueItem>(response.data)
    })
  }

  async function fetchItem(id: string) {
    await run(async () => {
      const response = await curatorService.getQueueItem(id)
      currentItem.value = response.data
    })
  }

  async function fetchStats() {
    try {
      const response = await curatorService.stats()
      stats.value = response.data
    } catch {
      // non-fatal
    }
  }

  async function approve(id: string) {
    await curatorService.approve(id)
    await fetchQueue()
  }

  async function reject(id: string, feedback: string) {
    await curatorService.reject(id, { curator_feedback: feedback })
    await fetchQueue()
  }

  async function requestChanges(id: string, feedback: string) {
    await curatorService.requestChanges(id, { curator_feedback: feedback })
    await fetchQueue()
  }

  return {
    queue,
    currentItem,
    stats,
    filters,
    loading,
    error,
    isEmpty,
    fetchQueue,
    fetchItem,
    fetchStats,
    approve,
    reject,
    requestChanges,
  }
})

