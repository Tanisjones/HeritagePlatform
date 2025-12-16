<script setup lang="ts">
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'

defineProps<{
  disabled?: boolean
}>()

const emit = defineEmits<{
  (e: 'approve'): void
  (e: 'reject', feedback: string): void
  (e: 'requestChanges', feedback: string): void
}>()

const { t } = useI18n()
const feedback = ref('')
</script>

<template>
  <section class="bg-white border border-gray-200 rounded-xl p-5">
    <h3 class="text-lg font-semibold text-gray-900 mb-3">{{ t('curatorReview.actions.title') }}</h3>
    <label class="block text-sm font-semibold text-gray-700 mb-1">{{ t('curatorReview.actions.feedbackLabel') }}</label>
    <textarea
      v-model="feedback"
      :disabled="disabled"
      rows="3"
      class="w-full rounded-lg border-gray-300 focus:ring-primary-500 focus:border-primary-500"
      :placeholder="t('curatorReview.actions.feedbackPlaceholder')"
    />

    <div class="mt-4 grid grid-cols-1 gap-2">
      <button
        type="button"
        :disabled="disabled"
        class="px-4 py-2 rounded-lg bg-green-600 text-white hover:bg-green-700 disabled:opacity-50"
        @click="emit('approve')"
      >
        {{ t('curatorReview.actions.approve') }}
      </button>
      <button
        type="button"
        :disabled="disabled"
        class="px-4 py-2 rounded-lg bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50"
        @click="emit('requestChanges', feedback)"
      >
        {{ t('curatorReview.actions.requestChanges') }}
      </button>
      <button
        type="button"
        :disabled="disabled"
        class="px-4 py-2 rounded-lg bg-red-600 text-white hover:bg-red-700 disabled:opacity-50"
        @click="emit('reject', feedback)"
      >
        {{ t('curatorReview.actions.reject') }}
      </button>
    </div>
  </section>
</template>

