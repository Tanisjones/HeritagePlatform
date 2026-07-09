<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import type { CuratorQueueItem } from '@/types/moderation'
import { useAuthStore } from '@/stores/auth'
import { useCityStore } from '@/stores/city'

const props = defineProps<{
  items: CuratorQueueItem[]
  loading?: boolean
  /** D2 — selected item ids for the bulk bar (v-model:selected). */
  selected?: string[]
}>()

const emit = defineEmits<{
  (e: 'select', id: string): void
  (e: 'update:selected', value: string[]): void
  (e: 'assign', id: string): void
}>()

const { t } = useI18n()
const authStore = useAuthStore()
const cityStore = useCityStore()

const statusPill = (status: string) => {
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

// ---- D2: selection ---------------------------------------------------------

// Only items still in the moderation flow can take a bulk decision.
const isDecidable = (item: CuratorQueueItem) =>
  item.status === 'pending' || item.status === 'changes_requested'

const decidableIds = computed(() => props.items.filter(isDecidable).map((i) => i.id))
const selectedSet = computed(() => new Set(props.selected ?? []))
const allSelected = computed(
  () => decidableIds.value.length > 0 && decidableIds.value.every((id) => selectedSet.value.has(id))
)

const toggleRow = (id: string) => {
  const next = new Set(selectedSet.value)
  if (next.has(id)) next.delete(id)
  else next.add(id)
  emit('update:selected', [...next])
}

const toggleAll = () => {
  emit('update:selected', allSelected.value ? [] : [...decidableIds.value])
}

// ---- D2: submission age ----------------------------------------------------

const ageDays = (item: CuratorQueueItem): number | null => {
  const raw = item.submission_date || item.created_at
  if (!raw) return null
  const ms = Date.now() - new Date(raw).getTime()
  if (!Number.isFinite(ms)) return null
  return Math.max(0, Math.floor(ms / 86_400_000))
}

// Waiting-time heat: fresh → neutral, 4-7 days → amber, older → red.
const ageClass = (days: number | null) => {
  if (days === null) return 'bg-gray-100 text-gray-600'
  if (days <= 3) return 'bg-gray-100 text-gray-600'
  if (days <= 7) return 'bg-amber-100 text-amber-800'
  return 'bg-red-100 text-red-800'
}

// ---- D2: assignee ----------------------------------------------------------

const isMine = (item: CuratorQueueItem) =>
  !!item.curator_email && item.curator_email === authStore.user?.email
</script>

<template>
  <div class="bg-white border border-gray-200 rounded-xl overflow-hidden">
    <div v-if="loading" class="p-6 text-sm text-gray-600">{{ t('curatorQueue.table.loading') }}</div>
    <div v-else-if="items.length === 0" class="p-6 text-sm text-gray-600">{{ t('curatorQueue.table.empty') }}</div>
    <table v-else class="min-w-full divide-y divide-gray-200">
      <thead class="bg-gray-50">
        <tr>
          <th class="px-4 py-3 w-8">
            <input
              type="checkbox"
              class="rounded border-gray-300"
              :checked="allSelected"
              :disabled="decidableIds.length === 0"
              :aria-label="t('curatorQueue.bulk.selectAll')"
              @change="toggleAll"
            />
          </th>
          <th class="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">{{ t('curatorQueue.table.title') }}</th>
          <th class="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">{{ t('curatorQueue.table.status') }}</th>
          <th class="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">{{ t('curatorQueue.table.assignee') }}</th>
          <th class="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">{{ t('curatorQueue.table.flags') }}</th>
          <th class="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">{{ t('curatorQueue.table.score') }}</th>
          <th class="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">{{ t('curatorQueue.table.submitted') }}</th>
        </tr>
      </thead>
      <tbody class="divide-y divide-gray-100">
        <tr
          v-for="item in items"
          :key="item.id"
          class="hover:bg-gray-50 cursor-pointer"
          @click="emit('select', item.id)"
        >
          <td class="px-4 py-3" @click.stop>
            <input
              v-if="isDecidable(item)"
              type="checkbox"
              class="rounded border-gray-300"
              :checked="selectedSet.has(item.id)"
              @change="toggleRow(item.id)"
            />
          </td>
          <td class="px-4 py-3">
            <div class="font-medium text-gray-900 flex items-center gap-2">
              <span>{{ item.title }}</span>
              <!-- C1: which city the item belongs to, when the queue is unscoped -->
              <span
                v-if="cityStore.isAllCities && item.city"
                class="text-xs font-medium rounded-full bg-secondary-100 text-secondary-800 px-2 py-0.5"
              >
                {{ item.city.name }}
              </span>
            </div>
            <div class="text-xs text-gray-500 line-clamp-1">{{ item.description }}</div>
          </td>
          <td class="px-4 py-3">
            <span class="inline-flex items-center px-2 py-1 rounded-full text-xs border" :class="statusPill(item.status)">
              {{ t(`curatorReview.statusMap.${item.status}`) }}
            </span>
          </td>
          <td class="px-4 py-3 text-sm" @click.stop>
            <span v-if="isMine(item)" class="text-xs font-semibold text-green-700 bg-green-50 border border-green-100 rounded-full px-2 py-0.5">
              {{ t('curatorQueue.table.you') }}
            </span>
            <span v-else-if="item.curator_email" class="text-xs text-gray-600" :title="item.curator_email">
              {{ item.curator_email.split('@')[0] }}
            </span>
            <button
              v-else-if="isDecidable(item)"
              class="text-xs font-medium text-primary-700 hover:text-primary-900 underline"
              @click="emit('assign', item.id)"
            >
              {{ t('curatorQueue.table.assignToMe') }}
            </button>
            <span v-else class="text-xs text-gray-400">—</span>
          </td>
          <td class="px-4 py-3 text-sm text-gray-700">{{ item.flags_open ?? 0 }}</td>
          <td class="px-4 py-3 text-sm text-gray-700">{{ item.total_score ?? '—' }}</td>
          <td class="px-4 py-3 text-sm text-gray-700">
            <div class="flex items-center gap-2">
              <span>{{ (item.submission_date || item.created_at || '').slice(0, 10) }}</span>
              <!-- D2: waiting-time heat so old submissions stand out -->
              <span
                v-if="ageDays(item) !== null"
                class="text-xs font-medium rounded-full px-2 py-0.5"
                :class="ageClass(ageDays(item))"
              >
                {{ t('curatorQueue.table.age', { days: ageDays(item) }) }}
              </span>
            </div>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
