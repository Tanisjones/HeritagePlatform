<script setup lang="ts">
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import type { CuratorNote } from '@/types/moderation'

defineProps<{
  notes: CuratorNote[]
  disabled?: boolean
}>()

const emit = defineEmits<{
  (e: 'add', payload: { content: string; is_pinned: boolean }): void
}>()

const { t } = useI18n()
const content = ref('')
const isPinned = ref(false)

function add() {
  if (!content.value.trim()) return
  emit('add', { content: content.value.trim(), is_pinned: isPinned.value })
  content.value = ''
  isPinned.value = false
}
</script>

<template>
  <section class="bg-white border border-gray-200 rounded-xl p-5">
    <h3 class="text-lg font-semibold text-gray-900 mb-4">{{ t('curatorReview.notes.title') }}</h3>

    <div class="space-y-2 mb-4">
      <div
        v-for="n in notes"
        :key="n.id"
        class="rounded-lg border border-gray-200 p-3"
        :class="n.is_pinned ? 'bg-yellow-50 border-yellow-200' : 'bg-white'"
      >
        <div class="flex items-center justify-between">
          <div class="text-xs font-semibold text-gray-600">{{ n.is_pinned ? t('curatorReview.notes.pinned') : t('curatorReview.notes.note') }}</div>
          <div class="text-xs text-gray-500">{{ n.created_at.slice(0, 19).replace('T', ' ') }}</div>
        </div>
        <div class="text-sm text-gray-900 mt-1 whitespace-pre-wrap">{{ n.content }}</div>
      </div>
      <div v-if="notes.length === 0" class="text-sm text-gray-600">{{ t('curatorReview.notes.empty') }}</div>
    </div>

    <div class="space-y-2">
      <textarea
        v-model="content"
        :disabled="disabled"
        rows="3"
        class="w-full rounded-lg border-gray-300 focus:ring-primary-500 focus:border-primary-500"
        :placeholder="t('curatorReview.notes.placeholder')"
      />
      <label class="flex items-center gap-2 text-sm text-gray-700">
        <input v-model="isPinned" :disabled="disabled" type="checkbox" />
        {{ t('curatorReview.notes.pinAction') }}
      </label>
      <button
        type="button"
        :disabled="disabled || !content.trim()"
        class="w-full inline-flex justify-center px-4 py-2 bg-gray-900 text-white rounded-lg hover:bg-black disabled:opacity-50"
        @click="add"
      >
        {{ t('curatorReview.notes.add') }}
      </button>
    </div>
  </section>
</template>

