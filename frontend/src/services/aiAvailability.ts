import { computed, ref } from 'vue'
import { aiService } from '@/services/api'

const available = ref<boolean | null>(null)
const loading = ref(false)

export function useAIAvailability() {
  const isAvailable = computed(() => available.value === true)
  const isKnown = computed(() => available.value !== null)

  async function refresh() {
    if (loading.value) return
    loading.value = true
    try {
      const res = await aiService.status()
      available.value = Boolean(res.available)
    } catch {
      available.value = false
    } finally {
      loading.value = false
    }
  }

  function markUnavailable() {
    available.value = false
  }

  return { isAvailable, isKnown, loading, refresh, markUnavailable }
}

