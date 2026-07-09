<script setup lang="ts">
import { useI18n } from 'vue-i18n'

defineProps<{
  contribution: any
}>()

const emit = defineEmits<{
  (e: 'open', id: string): void
  (e: 'edit', id: string): void
  (e: 'feedback', id: string): void
  (e: 'submit', id: string): void
}>()

const { t } = useI18n()

const statusStyle = (status: string) => {
  switch (status) {
    case 'pending':
      return 'bg-amber-50 text-amber-800 border-amber-100'
    case 'changes_requested':
      return 'bg-primary-50 text-primary-800 border-primary-100'
    case 'published':
      return 'bg-green-50 text-green-800 border-green-100'
    case 'rejected':
      return 'bg-red-50 text-red-800 border-red-100'
    default:
      return 'bg-gray-100 text-gray-700 border-gray-200'
  }
}
</script>

<template>
  <article class="bg-white border border-gray-200 rounded-xl p-5 hover:shadow-sm transition">
    <div class="flex items-start justify-between gap-4">
      <div>
        <h3 class="text-lg font-semibold text-gray-900">{{ contribution.title }}</h3>
        <p class="text-sm text-gray-600 mt-1 line-clamp-2">{{ contribution.description }}</p>
      </div>
      <span class="inline-flex items-center px-2 py-1 rounded-full text-xs border" :class="statusStyle(contribution.status)">
        {{ contribution.status }}
      </span>
    </div>

    <div class="mt-4 flex items-center justify-between">
      <div class="text-xs text-gray-500">
        Submitted: {{ (contribution.submission_date || contribution.created_at || '').slice(0, 10) }}
      </div>
      <div class="flex gap-2">
        <button
          class="px-3 py-2 text-sm rounded-lg border border-gray-200 hover:bg-gray-50"
          @click="emit('feedback', contribution.id)"
        >
          Feedback
        </button>
        <button
          class="px-3 py-2 text-sm rounded-lg bg-primary-600 text-white hover:bg-primary-700"
          @click="emit('edit', contribution.id)"
        >
          Edit
        </button>
        <!-- B2: drafts stay out of the queue until explicitly sent to review. -->
        <button
          v-if="contribution.status === 'draft'"
          class="px-3 py-2 text-sm rounded-lg bg-green-600 text-white hover:bg-green-700"
          @click="emit('submit', contribution.id)"
        >
          {{ t('myContributions.submitDraft') }}
        </button>
      </div>
    </div>
  </article>
</template>

