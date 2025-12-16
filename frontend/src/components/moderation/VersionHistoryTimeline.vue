<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import type { ContributionVersion } from '@/types/moderation'

defineProps<{
  versions: ContributionVersion[]
}>()

const { t } = useI18n()
</script>

<template>
  <section class="bg-white border border-gray-200 rounded-xl p-5">
    <h3 class="text-lg font-semibold text-gray-900 mb-4">{{ t('curatorReview.history.title') }}</h3>
    <div v-if="versions.length === 0" class="text-sm text-gray-600">{{ t('curatorReview.history.empty') }}</div>
    <ol v-else class="space-y-3">
      <li v-for="v in versions" :key="v.id" class="flex gap-3">
        <div class="mt-1 h-2 w-2 rounded-full bg-primary-600"></div>
        <div class="flex-1">
          <div class="flex items-center justify-between">
            <div class="text-sm font-medium text-gray-900">v{{ v.version_number }} ({{ v.created_by_type }})</div>
            <div class="text-xs text-gray-500">{{ v.created_at.slice(0, 19).replace('T', ' ') }}</div>
          </div>
          <div class="text-sm text-gray-700 mt-1">{{ v.changes_summary || '—' }}</div>
        </div>
      </li>
    </ol>
  </section>
</template>

