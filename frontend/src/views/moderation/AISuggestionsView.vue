<script setup lang="ts">
import { onMounted, ref } from 'vue'
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
const actingId = ref<string | null>(null)

const fetchSuggestions = async () => {
  loading.value = true
  error.value = null
  try {
    const params = statusFilter.value === 'all' ? {} : { status: statusFilter.value }
    const res = await aiSuggestionService.list(params)
    suggestions.value = res.data?.results ?? res.data ?? []
  } catch (e: any) {
    error.value = e?.message || t('aiSuggestions.loadError')
  } finally {
    loading.value = false
  }
}

const act = async (id: string, action: 'approve' | 'reject') => {
  actingId.value = id
  error.value = null
  try {
    if (action === 'approve') {
      await aiSuggestionService.approve(id)
    } else {
      await aiSuggestionService.reject(id)
    }
    await fetchSuggestions()
  } catch (e: any) {
    error.value = e?.message || t('aiSuggestions.actionError')
  } finally {
    actingId.value = null
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
          @change="fetchSuggestions"
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
            <span class="inline-block px-2 py-0.5 text-xs rounded-full bg-indigo-100 text-indigo-800">
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
            :disabled="actingId === s.id"
            @click="act(s.id, 'approve')"
          >
            {{ t('aiSuggestions.approve') }}
          </button>
          <button
            class="px-3 py-1.5 rounded-lg border border-gray-300 text-gray-700 text-sm hover:bg-gray-50 disabled:opacity-50"
            :disabled="actingId === s.id"
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
    </div>
  </div>
</template>
