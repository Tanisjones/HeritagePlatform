<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import type { QualityScore } from '@/types/moderation'

const { t } = useI18n()

const props = defineProps<{
  modelValue: QualityScore
  disabled?: boolean
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: QualityScore): void
  (e: 'save'): void
}>()

const completeness = ref(props.modelValue.completeness_score ?? 0)
const accuracy = ref(props.modelValue.accuracy_score ?? 0)
const media = ref(props.modelValue.media_quality_score ?? 0)
const notes = ref(props.modelValue.notes ?? '')

watch(
  () => props.modelValue,
  (v) => {
    completeness.value = v.completeness_score ?? 0
    accuracy.value = v.accuracy_score ?? 0
    media.value = v.media_quality_score ?? 0
    notes.value = v.notes ?? ''
  }
)

const total = computed(() => Number(completeness.value) + Number(accuracy.value) + Number(media.value))

watch([completeness, accuracy, media, notes], () => {
  emit('update:modelValue', {
    ...props.modelValue,
    completeness_score: Number(completeness.value),
    accuracy_score: Number(accuracy.value),
    media_quality_score: Number(media.value),
    total_score: total.value,
    notes: notes.value,
  })
})
</script>

<template>
  <section class="bg-white border border-gray-200 rounded-xl p-5">
    <div class="flex items-center justify-between mb-4">
      <h3 class="text-lg font-semibold text-gray-900">{{ t('curatorReview.qualityScore.title') }}</h3>
      <div class="text-sm font-semibold text-gray-700">{{ t('curatorReview.qualityScore.total', { total: total }) }}</div>
    </div>

    <div class="space-y-4">
      <div>
        <div class="flex justify-between text-sm text-gray-700 mb-1">
          <span>{{ t('curatorReview.qualityScore.completeness') }}</span>
          <span>{{ completeness }}/40</span>
        </div>
        <input v-model="completeness" :disabled="disabled" type="range" min="0" max="40" class="w-full" />
      </div>

      <div>
        <div class="flex justify-between text-sm text-gray-700 mb-1">
          <span>{{ t('curatorReview.qualityScore.accuracy') }}</span>
          <span>{{ accuracy }}/30</span>
        </div>
        <input v-model="accuracy" :disabled="disabled" type="range" min="0" max="30" class="w-full" />
      </div>

      <div>
        <div class="flex justify-between text-sm text-gray-700 mb-1">
          <span>{{ t('curatorReview.qualityScore.mediaQuality') }}</span>
          <span>{{ media }}/30</span>
        </div>
        <input v-model="media" :disabled="disabled" type="range" min="0" max="30" class="w-full" />
      </div>

      <div>
        <label class="block text-sm font-semibold text-gray-700 mb-1">{{ t('curatorReview.qualityScore.notes') }}</label>
        <textarea
          v-model="notes"
          :disabled="disabled"
          rows="3"
          class="w-full rounded-lg border-gray-300 focus:ring-primary-500 focus:border-primary-500"
          :placeholder="t('curatorReview.qualityScore.placeholder')"
        />
      </div>

      <button
        type="button"
        :disabled="disabled"
        class="w-full inline-flex justify-center px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50"
        @click="emit('save')"
      >
        {{ t('curatorReview.qualityScore.save') }}
      </button>
    </div>
  </section>
</template>
