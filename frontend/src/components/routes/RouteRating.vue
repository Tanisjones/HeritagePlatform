<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import AppButton from '@/components/common/AppButton.vue'

const { t } = useI18n()

const props = defineProps<{
  initialRating?: number | null
  initialComment?: string
  disabled?: boolean
  loading?: boolean
}>()

const emit = defineEmits<{
  submit: [payload: { rating: number; comment?: string }]
}>()

const rating = ref<number>(props.initialRating ?? 0)
const comment = ref<string>(props.initialComment ?? '')

watch(
  () => props.initialRating,
  (v) => {
    if (typeof v === 'number') rating.value = v
  }
)

const canSubmit = computed(() => rating.value >= 1 && rating.value <= 5 && !props.disabled && !props.loading)
</script>

<template>
  <section class="bg-white border border-gray-200 rounded-xl p-5">
    <h3 class="text-lg font-semibold text-gray-900 mb-3">{{ t('routesUi.rating.title') }}</h3>
    <div class="flex items-center gap-2 mb-3">
      <button
        v-for="i in 5"
        :key="i"
        type="button"
        class="text-2xl leading-none"
        :class="i <= rating ? 'text-yellow-500' : 'text-gray-300'"
        :disabled="disabled || loading"
        @click="rating = i"
      >
        ★
      </button>
      <span v-if="rating" class="text-sm text-gray-600">{{ t('routesUi.rating.outOfFive', { rating }) }}</span>
    </div>
    <textarea
      v-model="comment"
      class="w-full border border-gray-300 rounded-lg p-3 text-sm"
      rows="3"
      :placeholder="t('routesUi.rating.optionalCommentPlaceholder')"
      :disabled="disabled || loading"
    />
    <div class="mt-3 flex justify-end">
      <AppButton :loading="loading" :disabled="!canSubmit" @click="emit('submit', { rating, comment: comment.trim() || undefined })">
        {{ t('routesUi.rating.submit') }}
      </AppButton>
    </div>
  </section>
</template>
