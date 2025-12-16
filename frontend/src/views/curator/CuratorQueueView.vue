<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import CuratorQueueFilters from '@/components/moderation/CuratorQueueFilters.vue'
import CuratorQueueTable from '@/components/moderation/CuratorQueueTable.vue'
import { useModerationStore } from '@/stores/moderation'

const router = useRouter()
const { t } = useI18n()
const moderationStore = useModerationStore()
const localFilters = ref<Record<string, any>>({ ...moderationStore.filters })

async function apply() {
  moderationStore.filters = localFilters.value
  await moderationStore.fetchQueue()
}

onMounted(async () => {
  await moderationStore.fetchQueue()
})
</script>

<template>
  <div class="container mx-auto px-4 py-8 space-y-4">
    <div class="flex items-center justify-between">
      <h1 class="text-3xl font-bold text-gray-900">{{ t('curatorQueue.title') }}</h1>
      <button
        class="px-4 py-2 rounded-lg border border-gray-200 hover:bg-gray-50"
        @click="moderationStore.fetchQueue()"
      >
        {{ t('curatorQueue.refresh') }}
      </button>
    </div>

    <CuratorQueueFilters v-model="localFilters" @apply="apply" />

    <div v-if="moderationStore.error" class="bg-red-50 border border-red-200 text-red-800 px-4 py-3 rounded-lg">
      {{ moderationStore.error }}
    </div>

    <CuratorQueueTable
      :items="moderationStore.queue"
      :loading="moderationStore.loading"
      @select="(id) => router.push(`/moderation/queue/${id}`)"
    />
  </div>
</template>

