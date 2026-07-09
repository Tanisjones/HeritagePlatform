<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import CuratorQueueFilters from '@/components/moderation/CuratorQueueFilters.vue'
import CuratorQueueTable from '@/components/moderation/CuratorQueueTable.vue'
import ErrorBanner from '@/components/common/ErrorBanner.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import { useModerationStore } from '@/stores/moderation'
import { useConfirm, useToast } from '@/composables/useDialogs'

const router = useRouter()
const { t } = useI18n()
const moderationStore = useModerationStore()
const { confirm } = useConfirm()
const toast = useToast()
const localFilters = ref<Record<string, any>>({ ...moderationStore.filters })

// D2 — bulk selection + decisions.
const selected = ref<string[]>([])
const rejectArmed = ref(false)
const rejectFeedback = ref('')
const bulkBusy = ref(false)

async function apply() {
  moderationStore.filters = localFilters.value
  selected.value = []
  await moderationStore.fetchQueue()
}

async function assign(id: string) {
  try {
    await moderationStore.assign(id)
  } catch {
    toast.error(t('curatorQueue.bulk.error'))
  }
}

async function bulkApprove() {
  if (bulkBusy.value || !selected.value.length) return
  const ok = await confirm({
    message: t('curatorQueue.bulk.confirmApprove', { count: selected.value.length }),
  })
  if (!ok) return
  await runBulk('approve')
}

async function bulkReject() {
  // First click arms the inline feedback; second confirms.
  if (!rejectArmed.value) {
    rejectArmed.value = true
    return
  }
  await runBulk('reject', rejectFeedback.value.trim())
}

async function runBulk(decision: 'approve' | 'reject', feedback = '') {
  bulkBusy.value = true
  try {
    const report = await moderationStore.bulkDecide(selected.value, decision, feedback)
    const message = report.skipped.length
      ? t('curatorQueue.bulk.doneWithSkipped', { done: report.processed.length, skipped: report.skipped.length })
      : t('curatorQueue.bulk.done', { done: report.processed.length })
    toast.success(message)
    selected.value = []
    rejectArmed.value = false
    rejectFeedback.value = ''
  } catch {
    toast.error(t('curatorQueue.bulk.error'))
  } finally {
    bulkBusy.value = false
  }
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

    <ErrorBanner :message="moderationStore.error" @retry="moderationStore.fetchQueue()" />

    <!-- D2: bulk decision bar -->
    <div
      v-if="selected.length"
      class="bg-white border border-primary-200 rounded-xl p-4 space-y-3"
    >
      <div class="flex flex-wrap items-center gap-3">
        <span class="text-sm font-medium text-gray-800">
          {{ t('curatorQueue.bulk.selected', { count: selected.length }) }}
        </span>
        <button
          class="px-4 py-2 rounded-lg bg-green-600 text-white hover:bg-green-700 disabled:opacity-50 text-sm font-medium"
          :disabled="bulkBusy"
          @click="bulkApprove"
        >
          {{ t('curatorQueue.bulk.approve', { count: selected.length }) }}
        </button>
        <button
          class="px-4 py-2 rounded-lg bg-red-600 text-white hover:bg-red-700 disabled:opacity-50 text-sm font-medium"
          :disabled="bulkBusy"
          @click="bulkReject"
        >
          {{ rejectArmed ? t('curatorQueue.bulk.confirmReject', { count: selected.length }) : t('curatorQueue.bulk.reject', { count: selected.length }) }}
        </button>
        <button
          class="text-sm text-gray-500 hover:text-gray-800 underline"
          :disabled="bulkBusy"
          @click="selected = []; rejectArmed = false"
        >
          {{ t('curatorQueue.bulk.clear') }}
        </button>
      </div>
      <div v-if="rejectArmed">
        <label class="block text-xs font-semibold text-gray-600 mb-1">
          {{ t('curatorQueue.bulk.feedbackLabel') }}
        </label>
        <textarea
          v-model="rejectFeedback"
          rows="2"
          class="w-full rounded-lg border-gray-300 text-sm"
          :placeholder="t('curatorQueue.bulk.feedbackPlaceholder')"
        />
      </div>
    </div>

    <EmptyState
      v-if="!moderationStore.error && moderationStore.isEmpty"
      :title="t('curatorQueue.empty')"
    />

    <CuratorQueueTable
      v-else
      v-model:selected="selected"
      :items="moderationStore.queue"
      :loading="moderationStore.loading"
      @select="(id) => router.push(`/moderation/queue/${id}`)"
      @assign="assign"
    />
  </div>
</template>
