import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { contributorService } from '@/services/api'
import { withLoading } from '@/composables/useAsyncAction'
import { unwrapResults } from '@/utils/pagination'
import type { ContributorFeedback } from '@/types/moderation'

export const useContributionsStore = defineStore('contributions', () => {
  const myContributions = ref<any[]>([])
  const currentContribution = ref<any | null>(null)
  const currentFeedback = ref<ContributorFeedback | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  const isEmpty = computed(() => !loading.value && myContributions.value.length === 0)

  // These fetches swallow errors into the `error` ref (no rethrow) — views bind it.
  const run = <T>(fn: () => Promise<T>) => withLoading(loading, error, fn)

  async function fetchMyContributions(params?: Record<string, any>) {
    await run(async () => {
      const response = await contributorService.list(params)
      myContributions.value = unwrapResults(response.data)
    })
  }

  async function fetchContribution(id: string) {
    await run(async () => {
      const response = await contributorService.get(id)
      currentContribution.value = response.data
    })
  }

  async function fetchFeedback(id: string) {
    await run(async () => {
      const response = await contributorService.feedback(id)
      currentFeedback.value = response.data
    })
  }

  async function updateContribution(id: string, payload: any) {
    const response = await contributorService.update(id, payload)
    currentContribution.value = response.data
    return response.data
  }

  async function resubmit(id: string) {
    await contributorService.resubmit(id)
    await fetchMyContributions()
  }

  /** B2 — draft → pending, then refresh the list so the card status updates. */
  async function submitDraft(id: string) {
    await contributorService.submit(id)
    await fetchMyContributions()
  }

  return {
    myContributions,
    currentContribution,
    currentFeedback,
    loading,
    error,
    isEmpty,
    fetchMyContributions,
    fetchContribution,
    fetchFeedback,
    updateContribution,
    resubmit,
    submitDraft,
  }
})

