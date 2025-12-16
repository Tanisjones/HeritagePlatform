<script setup lang="ts">
import type { ContributorFeedback } from '@/types/moderation'

defineProps<{
  feedback: ContributorFeedback | null
}>()

const pill = (status: string) => {
  switch (status) {
    case 'pending':
      return 'bg-amber-50 text-amber-800 border-amber-100'
    case 'changes_requested':
      return 'bg-blue-50 text-blue-800 border-blue-100'
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
  <section class="bg-white border border-gray-200 rounded-xl p-5">
    <div class="flex items-center justify-between mb-3">
      <h3 class="text-lg font-semibold text-gray-900">Curator feedback</h3>
      <span
        v-if="feedback"
        class="inline-flex items-center px-2 py-1 rounded-full text-xs border"
        :class="pill(feedback.status)"
      >
        {{ feedback.status }}
      </span>
    </div>

    <div v-if="!feedback" class="text-sm text-gray-600">No feedback available.</div>

    <div v-else class="space-y-4">
      <div>
        <div class="text-sm font-semibold text-gray-700 mb-1">Message</div>
        <div class="text-sm text-gray-900 whitespace-pre-wrap">
          {{ feedback.curator_feedback || '—' }}
        </div>
      </div>

      <div v-if="feedback.quality_score" class="grid grid-cols-2 md:grid-cols-4 gap-3">
        <div class="rounded-lg border border-gray-200 p-3">
          <div class="text-xs text-gray-600">Total</div>
          <div class="text-xl font-bold text-gray-900">{{ feedback.quality_score.total_score ?? '—' }}</div>
        </div>
        <div class="rounded-lg border border-gray-200 p-3">
          <div class="text-xs text-gray-600">Completeness</div>
          <div class="text-xl font-bold text-gray-900">{{ feedback.quality_score.completeness_score }}</div>
        </div>
        <div class="rounded-lg border border-gray-200 p-3">
          <div class="text-xs text-gray-600">Accuracy</div>
          <div class="text-xl font-bold text-gray-900">{{ feedback.quality_score.accuracy_score }}</div>
        </div>
        <div class="rounded-lg border border-gray-200 p-3">
          <div class="text-xs text-gray-600">Media</div>
          <div class="text-xl font-bold text-gray-900">{{ feedback.quality_score.media_quality_score }}</div>
        </div>
      </div>
    </div>
  </section>
</template>

