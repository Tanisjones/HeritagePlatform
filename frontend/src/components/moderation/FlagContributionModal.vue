<script setup lang="ts">
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import type { FlagType } from '@/types/moderation'

const props = defineProps<{
  open: boolean
}>()

const emit = defineEmits<{
  (e: 'close'): void
  (e: 'submit', payload: { flag_type: FlagType; reason: string }): void
}>()

const { t } = useI18n()
const flagType = ref<FlagType>('inaccurate')
const reason = ref('')

function submit() {
  emit('submit', { flag_type: flagType.value, reason: reason.value })
}
</script>

<template>
  <div v-if="open" class="fixed inset-0 z-50 flex items-center justify-center">
    <div class="absolute inset-0 bg-black/40" @click="emit('close')"></div>
    <div class="relative bg-white rounded-xl shadow-xl w-full max-w-lg p-6">
      <div class="flex items-start justify-between">
        <h3 class="text-lg font-semibold text-gray-900">{{ t('curatorReview.flagModal.title') }}</h3>
        <button class="text-gray-500 hover:text-gray-800" @click="emit('close')">✕</button>
      </div>

      <div class="mt-4 space-y-4">
        <div>
          <label class="block text-sm font-semibold text-gray-700 mb-1">{{ t('curatorReview.flagModal.type') }}</label>
          <select v-model="flagType" class="w-full rounded-lg border-gray-300">
            <option value="spam">{{ t('curatorReview.flagModal.types.spam') }}</option>
            <option value="inappropriate">{{ t('curatorReview.flagModal.types.inappropriate') }}</option>
            <option value="duplicate">{{ t('curatorReview.flagModal.types.duplicate') }}</option>
            <option value="expert_review_needed">{{ t('curatorReview.flagModal.types.expert_review_needed') }}</option>
            <option value="copyright_issue">{{ t('curatorReview.flagModal.types.copyright_issue') }}</option>
            <option value="inaccurate">{{ t('curatorReview.flagModal.types.inaccurate') }}</option>
          </select>
        </div>
        <div>
          <label class="block text-sm font-semibold text-gray-700 mb-1">{{ t('curatorReview.flagModal.reason') }}</label>
          <textarea v-model="reason" rows="3" class="w-full rounded-lg border-gray-300" :placeholder="t('curatorReview.flagModal.placeholder')" />
        </div>
      </div>

      <div class="mt-6 flex justify-end gap-2">
        <button class="px-4 py-2 rounded-lg border border-gray-200" @click="emit('close')">{{ t('curatorReview.flagModal.cancel') }}</button>
        <button class="px-4 py-2 rounded-lg bg-red-600 text-white hover:bg-red-700" @click="submit">{{ t('curatorReview.flagModal.submit') }}</button>
      </div>
    </div>
  </div>
</template>

