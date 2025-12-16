<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import type { ReviewChecklist, ReviewChecklistResponse } from '@/types/moderation'

const props = defineProps<{
  checklist: ReviewChecklist | null
  responses: ReviewChecklistResponse[]
  disabled?: boolean
}>()

const emit = defineEmits<{
  (e: 'update:responses', value: ReviewChecklistResponse[]): void
  (e: 'save'): void
}>()

const { t } = useI18n()
const local = ref<ReviewChecklistResponse[]>([])

watch(
  () => props.responses,
  (v) => {
    local.value = v.map((r) => ({ ...r }))
  },
  { immediate: true }
)

const byItemId = computed(() => {
  const map = new Map<string, ReviewChecklistResponse>()
  for (const resp of local.value) map.set(resp.checklist_item, resp)
  return map
})

function toggle(itemId: string, checked: boolean) {
  const existing = byItemId.value.get(itemId)
  const next = existing
    ? { ...existing, is_checked: checked }
    : ({
        heritage_item: local.value[0]?.heritage_item || '',
        checklist_item: itemId,
        is_checked: checked,
        notes: '',
      } as ReviewChecklistResponse)

  const without = local.value.filter((r) => r.checklist_item !== itemId)
  local.value = [...without, next]
  emit('update:responses', local.value)
}

function setNotes(itemId: string, notes: string) {
  const existing = byItemId.value.get(itemId)
  if (!existing) return
  const without = local.value.filter((r) => r.checklist_item !== itemId)
  local.value = [...without, { ...existing, notes }]
  emit('update:responses', local.value)
}
</script>

<template>
  <section class="bg-white border border-gray-200 rounded-xl p-5">
    <div class="flex items-center justify-between mb-4">
      <h3 class="text-lg font-semibold text-gray-900">{{ t('curatorReview.checklist.title') }}</h3>
      <button
        type="button"
        :disabled="disabled || !checklist"
        class="inline-flex px-3 py-2 text-sm bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50"
        @click="emit('save')"
      >
        {{ t('curatorReview.checklist.save') }}
      </button>
    </div>

    <div v-if="!checklist" class="text-sm text-gray-600">{{ t('curatorReview.checklist.unavailable') }}</div>

    <div v-else class="space-y-3">
      <div
        v-for="item in checklist.items"
        :key="item.id"
        class="rounded-lg border border-gray-200 p-3"
      >
        <label class="flex items-start gap-3">
          <input
            type="checkbox"
            class="mt-1"
            :disabled="disabled"
            :checked="byItemId.get(item.id)?.is_checked ?? false"
            @change="toggle(item.id, ($event.target as HTMLInputElement).checked)"
          />
          <div class="flex-1">
            <div class="text-sm font-medium text-gray-900">
              {{ item.text }}
              <span v-if="item.is_required" class="text-xs text-red-600 ml-1">{{ t('curatorReview.checklist.required') }}</span>
            </div>
            <div v-if="item.help_text" class="text-xs text-gray-600 mt-1">{{ item.help_text }}</div>
            <textarea
              v-if="byItemId.get(item.id)"
              :disabled="disabled"
              rows="2"
              class="mt-2 w-full rounded-lg border-gray-300 focus:ring-primary-500 focus:border-primary-500 text-sm"
              :placeholder="t('curatorReview.checklist.notesPlaceholder')"
              :value="byItemId.get(item.id)?.notes ?? ''"
              @input="setNotes(item.id, ($event.target as HTMLTextAreaElement).value)"
            />
          </div>
        </label>
      </div>
    </div>
  </section>
</template>

