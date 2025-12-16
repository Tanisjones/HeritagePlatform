<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

const props = defineProps<{
  modelValue: Record<string, any>
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: Record<string, any>): void
  (e: 'apply'): void
}>()

const { t } = useI18n()

const status = computed({
  get: () => props.modelValue.status ?? 'pending',
  set: (value: string) => emit('update:modelValue', { ...props.modelValue, status: value }),
})

const search = computed({
  get: () => props.modelValue.search ?? '',
  set: (value: string) => emit('update:modelValue', { ...props.modelValue, search: value }),
})
</script>

<template>
  <div class="bg-white border border-gray-200 rounded-xl p-4 flex flex-col md:flex-row md:items-end gap-3">
    <div class="flex-1">
      <label class="block text-sm font-semibold text-gray-700 mb-1">{{ t('curatorQueue.filters.search') }}</label>
      <input
        v-model="search"
        type="text"
        class="w-full rounded-lg border-gray-300 focus:ring-primary-500 focus:border-primary-500"
        :placeholder="t('curatorQueue.filters.searchPlaceholder')"
      />
    </div>
    <div class="w-full md:w-56">
      <label class="block text-sm font-semibold text-gray-700 mb-1">{{ t('curatorQueue.filters.status') }}</label>
      <select
        v-model="status"
        class="w-full rounded-lg border-gray-300 focus:ring-primary-500 focus:border-primary-500"
      >
        <option value="pending">{{ t('curatorReview.statusMap.pending') }}</option>
        <option value="changes_requested">{{ t('curatorReview.statusMap.changes_requested') }}</option>
        <option value="published">{{ t('curatorReview.statusMap.published') }}</option>
        <option value="rejected">{{ t('curatorReview.statusMap.rejected') }}</option>
      </select>
    </div>
    <button
      type="button"
      class="inline-flex justify-center px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
      @click="emit('apply')"
    >
      {{ t('curatorQueue.filters.apply') }}
    </button>
  </div>
</template>

