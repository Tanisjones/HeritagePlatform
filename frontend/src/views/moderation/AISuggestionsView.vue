<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { aiSuggestionService } from '@/services/api'

interface AISuggestion {
  id: string
  heritage_item: string
  heritage_item_title?: string
  suggester: string
  suggestion_type: string
  content: unknown
  confidence: number | null
  status: 'pending' | 'approved' | 'rejected'
  created_at: string
}

const { t } = useI18n()

const suggestions = ref<AISuggestion[]>([])
const loading = ref(false)
const error = ref<string | null>(null)
const statusFilter = ref<string>('pending')
// Track in-flight rows in a Set so concurrent actions on different rows are
// each guarded (a single id would only debounce one row).
const actingIds = ref<Set<string>>(new Set())
const page = ref(1)
const count = ref(0)
const pageSize = ref(20)

const totalPages = computed(() => Math.max(1, Math.ceil(count.value / pageSize.value)))

const fetchSuggestions = async () => {
  loading.value = true
  error.value = null
  try {
    const params: Record<string, any> = { page: page.value }
    if (statusFilter.value !== 'all') params.status = statusFilter.value
    const res = await aiSuggestionService.list(params)
    const data = res.data
    if (Array.isArray(data)) {
      suggestions.value = data
      count.value = data.length
    } else {
      suggestions.value = data?.results ?? []
      count.value = typeof data?.count === 'number' ? data.count : suggestions.value.length
      if (Array.isArray(data?.results) && data.results.length) pageSize.value = data.results.length
    }
  } catch {
    error.value = t('aiSuggestions.loadError')
  } finally {
    loading.value = false
  }
}

const applyFilter = () => {
  page.value = 1
  fetchSuggestions()
}

const goToPage = (p: number) => {
  if (p < 1 || p > totalPages.value || p === page.value) return
  page.value = p
  fetchSuggestions()
}

const act = async (id: string, action: 'approve' | 'reject') => {
  if (actingIds.value.has(id)) return
  actingIds.value.add(id)
  error.value = null
  try {
    if (action === 'approve') {
      await aiSuggestionService.approve(id)
    } else {
      await aiSuggestionService.reject(id)
    }
    // Drop the acted row locally instead of a full refetch — avoids racing
    // overlapping refetches when several rows are actioned quickly.
    suggestions.value = suggestions.value.filter((s) => s.id !== id)
    count.value = Math.max(0, count.value - 1)
  } catch {
    error.value = t('aiSuggestions.actionError')
  } finally {
    actingIds.value.delete(id)
  }
}

const formatContent = (content: unknown): string => {
  if (Array.isArray(content)) return content.join(', ')
  if (content && typeof content === 'object') return JSON.stringify(content)
  return String(content ?? '')
}

onMounted(fetchSuggestions)
</script>

<template>
  <div class="container mx-auto px-4 py-8 space-y-4">
    <div class="flex items-center justify-between">
      <h1 class="text-3xl font-bold text-gray-900">{{ t('aiSuggestions.title') }}</h1>
      <div class="w-48">
        <select
          v-model="statusFilter"
          class="w-full rounded-lg border-gray-300"
          @change="applyFilter"
        >
          <option value="pending">{{ t('aiSuggestions.filters.pending') }}</option>
          <option value="approved">{{ t('aiSuggestions.filters.approved') }}</option>
          <option value="rejected">{{ t('aiSuggestions.filters.rejected') }}</option>
          <option value="all">{{ t('aiSuggestions.filters.all') }}</option>
        </select>
      </div>
    </div>

    <p class="text-sm text-gray-600">{{ t('aiSuggestions.intro') }}</p>

    <div v-if="error" class="bg-red-50 border border-red-200 text-red-800 px-4 py-3 rounded-lg">
      {{ error }}
    </div>

    <div v-if="loading" class="text-gray-600">{{ t('aiSuggestions.loading') }}</div>

    <div v-else class="space-y-3">
      <div
        v-for="s in suggestions"
        :key="s.id"
        class="bg-white border border-gray-200 rounded-xl p-4 flex items-start justify-between gap-4"
      >
        <div class="min-w-0">
          <div class="flex items-center gap-2 mb-1">
            <span class="inline-block px-2 py-0.5 text-xs rounded-full bg-primary-100 text-primary-800">
              {{ t(`aiSuggestions.types.${s.suggestion_type}`, s.suggestion_type) }}
            </span>
            <span class="text-xs text-gray-500">{{ s.suggester }}</span>
          </div>
          <p class="text-sm text-gray-900 break-words">{{ formatContent(s.content) }}</p>
          <p class="text-xs text-gray-500 mt-1">
            {{ t('aiSuggestions.forItem') }}:
            <span class="font-medium">{{ s.heritage_item_title || s.heritage_item }}</span>
          </p>
        </div>
        <div v-if="s.status === 'pending'" class="flex flex-col gap-2 shrink-0">
          <button
            class="px-3 py-1.5 rounded-lg bg-green-600 text-white text-sm hover:bg-green-700 disabled:opacity-50"
            :disabled="actingIds.has(s.id)"
            @click="act(s.id, 'approve')"
          >
            {{ t('aiSuggestions.approve') }}
          </button>
          <button
            class="px-3 py-1.5 rounded-lg border border-gray-300 text-gray-700 text-sm hover:bg-gray-50 disabled:opacity-50"
            :disabled="actingIds.has(s.id)"
            @click="act(s.id, 'reject')"
          >
            {{ t('aiSuggestions.reject') }}
          </button>
        </div>
        <span
          v-else
          class="shrink-0 text-xs px-2 py-1 rounded-full"
          :class="s.status === 'approved' ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-600'"
        >
          {{ t(`aiSuggestions.filters.${s.status}`) }}
        </span>
      </div>

      <div v-if="suggestions.length === 0" class="text-sm text-gray-600">
        {{ t('aiSuggestions.empty') }}
      </div>

      <div v-if="totalPages > 1" class="flex items-center justify-center gap-4 pt-2">
        <button
          class="px-3 py-1.5 rounded-lg border border-gray-300 text-gray-700 text-sm hover:bg-gray-50 disabled:opacity-50"
          :disabled="page <= 1"
          @click="goToPage(page - 1)"
        >
          {{ t('aiSuggestions.prev') }}
        </button>
        <span class="text-sm text-gray-600">{{ t('aiSuggestions.pageOf', { page, total: totalPages }) }}</span>
        <button
          class="px-3 py-1.5 rounded-lg border border-gray-300 text-gray-700 text-sm hover:bg-gray-50 disabled:opacity-50"
          :disabled="page >= totalPages"
          @click="goToPage(page + 1)"
        >
          {{ t('aiSuggestions.next') }}
        </button>
      </div>
    </div>
  </div>
</template>
