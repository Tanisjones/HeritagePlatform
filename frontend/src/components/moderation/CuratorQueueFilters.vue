<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '@/stores/auth'

const props = defineProps<{
  modelValue: Record<string, any>
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: Record<string, any>): void
  (e: 'apply'): void
}>()

const { t } = useI18n()
const authStore = useAuthStore()

const status = computed({
  get: () => props.modelValue.status ?? 'pending',
  set: (value: string) => emit('update:modelValue', { ...props.modelValue, status: value }),
})

const search = computed({
  get: () => props.modelValue.search ?? '',
  set: (value: string) => emit('update:modelValue', { ...props.modelValue, search: value }),
})

// D2 — "solo los míos": filters by the assignee (the API's ?curator= filter).
const onlyMine = computed({
  get: () => !!props.modelValue.curator,
  set: (value: boolean) => {
    const next = { ...props.modelValue }
    if (value && authStore.user?.id) next.curator = authStore.user.id
    else delete next.curator
    emit('update:modelValue', next)
  },
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
    <!-- D2: only items assigned to me -->
    <label class="flex items-center gap-2 text-sm text-gray-700 whitespace-nowrap pb-2 md:pb-2.5">
      <input v-model="onlyMine" type="checkbox" class="rounded border-gray-300" />
      {{ t('curatorQueue.filters.mine') }}
    </label>
    <button
      type="button"
      class="inline-flex justify-center px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700"
      @click="emit('apply')"
    >
      {{ t('curatorQueue.filters.apply') }}
    </button>
  </div>
</template>

