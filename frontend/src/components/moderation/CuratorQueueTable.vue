<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import type { CuratorQueueItem } from '@/types/moderation'

defineProps<{
  items: CuratorQueueItem[]
  loading?: boolean
}>()

const emit = defineEmits<{
  (e: 'select', id: string): void
}>()

const { t } = useI18n()

const statusPill = (status: string) => {
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
  <div class="bg-white border border-gray-200 rounded-xl overflow-hidden">
    <div v-if="loading" class="p-6 text-sm text-gray-600">{{ t('curatorQueue.table.loading') }}</div>
    <div v-else-if="items.length === 0" class="p-6 text-sm text-gray-600">{{ t('curatorQueue.table.empty') }}</div>
    <table v-else class="min-w-full divide-y divide-gray-200">
      <thead class="bg-gray-50">
        <tr>
          <th class="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">{{ t('curatorQueue.table.title') }}</th>
          <th class="px-4 py-3 text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">{{ t('curatorQueue.table.status') }}</th>
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
          <td class="px-4 py-3">
            <div class="font-medium text-gray-900">{{ item.title }}</div>
            <div class="text-xs text-gray-500 line-clamp-1">{{ item.description }}</div>
          </td>
          <td class="px-4 py-3">
            <span class="inline-flex items-center px-2 py-1 rounded-full text-xs border" :class="statusPill(item.status)">
              {{ t(`curatorReview.statusMap.${item.status}`) }}
            </span>
          </td>
          <td class="px-4 py-3 text-sm text-gray-700">{{ item.flags_open ?? 0 }}</td>
          <td class="px-4 py-3 text-sm text-gray-700">{{ item.total_score ?? '—' }}</td>
          <td class="px-4 py-3 text-sm text-gray-700">
            {{ (item.submission_date || item.created_at || '').slice(0, 10) }}
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

