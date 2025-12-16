import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { contributorService } from '@/services/api'
import type { ContributorFeedback } from '@/types/moderation'

export const useContributionsStore = defineStore('contributions', () => {
  const myContributions = ref<any[]>([])
  const currentContribution = ref<any | null>(null)
  const currentFeedback = ref<ContributorFeedback | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  const isEmpty = computed(() => !loading.value && myContributions.value.length === 0)

  async function fetchMyContributions(params?: Record<string, any>) {
    loading.value = true
    error.value = null
    try {
      const response = await contributorService.list(params)
      myContributions.value = response.data.results ?? response.data
    } catch (e: any) {
      error.value = e?.message ?? 'Failed to load contributions'
    } finally {
      loading.value = false
    }
  }

  async function fetchContribution(id: string) {
    loading.value = true
    error.value = null
    try {
      const response = await contributorService.get(id)
      currentContribution.value = response.data
    } catch (e: any) {
      error.value = e?.message ?? 'Failed to load contribution'
    } finally {
      loading.value = false
    }
  }

  async function fetchFeedback(id: string) {
    loading.value = true
    error.value = null
    try {
      const response = await contributorService.feedback(id)
      currentFeedback.value = response.data
    } catch (e: any) {
      error.value = e?.message ?? 'Failed to load feedback'
    } finally {
      loading.value = false
    }
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
  }
})

