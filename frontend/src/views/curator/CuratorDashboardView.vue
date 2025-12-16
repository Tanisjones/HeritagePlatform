<script setup lang="ts">
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useModerationStore } from '@/stores/moderation'
import { useI18n } from 'vue-i18n'

const router = useRouter()
const moderationStore = useModerationStore()
const { t } = useI18n()

onMounted(async () => {
  await moderationStore.fetchStats()
})
</script>

<template>
  <div class="container mx-auto px-4 py-8">
    <div class="flex items-center justify-between mb-6">
      <h1 class="text-3xl font-bold text-gray-900">{{ t('curator.title') }}</h1>
      <div class="flex gap-3">
        <button
          class="px-4 py-2 rounded-lg border border-primary-600 text-primary-600 hover:bg-primary-50 bg-white"
          @click="router.push('/moderation/resources')"
        >
          {{ t('curator.manageResources', 'Manage Resources') }}
        </button>
        <button
          class="px-4 py-2 rounded-lg bg-primary-600 text-white hover:bg-primary-700"
          @click="router.push('/moderation/queue')"
        >
          {{ t('curator.openQueue') }}
        </button>
      </div>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
      <div class="bg-white border border-gray-200 rounded-xl p-5">
        <div class="text-sm text-gray-600">{{ t('curator.stats.pending') }}</div>
        <div class="text-3xl font-bold text-gray-900">{{ moderationStore.stats?.pending ?? '—' }}</div>
      </div>
      <div class="bg-white border border-gray-200 rounded-xl p-5">
        <div class="text-sm text-gray-600">{{ t('curator.stats.changesRequested') }}</div>
        <div class="text-3xl font-bold text-gray-900">{{ moderationStore.stats?.changes_requested ?? '—' }}</div>
      </div>
      <div class="bg-white border border-gray-200 rounded-xl p-5">
        <div class="text-sm text-gray-600">{{ t('curator.stats.flaggedOpen') }}</div>
        <div class="text-3xl font-bold text-gray-900">{{ moderationStore.stats?.flagged_open ?? '—' }}</div>
      </div>
      <div class="bg-white border border-gray-200 rounded-xl p-5">
        <div class="text-sm text-gray-600">{{ t('curator.stats.reviewedTotal') }}</div>
        <div class="text-3xl font-bold text-gray-900">{{ moderationStore.stats?.reviewed_total ?? '—' }}</div>
      </div>
    </div>
  </div>
</template>

