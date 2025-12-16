import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { curatorService } from '@/services/api'
import type { CuratorQueueItem, CuratorReviewDetail, CuratorStats } from '@/types/moderation'

export const useModerationStore = defineStore('moderation', () => {
  const queue = ref<CuratorQueueItem[]>([])
  const currentItem = ref<CuratorReviewDetail | null>(null)
  const stats = ref<CuratorStats | null>(null)
  const filters = ref<Record<string, any>>({ status: 'pending' })
  const loading = ref(false)
  const error = ref<string | null>(null)

  const isEmpty = computed(() => !loading.value && queue.value.length === 0)

  async function fetchQueue(overrides?: Record<string, any>) {
    loading.value = true
    error.value = null
    try {
      const params = { ...filters.value, ...(overrides || {}) }
      const response = await curatorService.queue(params)
      queue.value = response.data.results ?? response.data
    } catch (e: any) {
      error.value = e?.message ?? 'Failed to load queue'
    } finally {
      loading.value = false
    }
  }

  async function fetchItem(id: string) {
    loading.value = true
    error.value = null
    try {
      const response = await curatorService.getQueueItem(id)
      currentItem.value = response.data
    } catch (e: any) {
      error.value = e?.message ?? 'Failed to load contribution'
    } finally {
      loading.value = false
    }
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

