<script setup lang="ts">
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useOfflineRoute } from '@/composables/useOfflineRoute'
import AppButton from '@/components/common/AppButton.vue'
import type { HeritageRoute } from '@/types/heritage'

/**
 * "Download for offline" control: pre-fetches this route's tiles + data + media
 * into the existing caches so it works with no coverage. Shows an estimate
 * before downloading, a progress bar during, and a "saved / remove" state after.
 */
const props = defineProps<{ route: HeritageRoute }>()

const { t } = useI18n()
const {
  downloading,
  progress,
  total,
  index,
  isSaved,
  estimateTileCount,
  downloadRouteForOffline,
  removeOfflineRoute,
} = useOfflineRoute()

const confirming = ref(false)

const saved = computed(() => isSaved(props.route.id))
const savedEntry = computed(() => index.value[props.route.id] ?? null)
const online = computed(() => (typeof navigator !== 'undefined' ? navigator.onLine : true))
const tileEstimate = computed(() => estimateTileCount(props.route))
const percent = computed(() => (total.value ? Math.round((progress.value / total.value) * 100) : 0))

async function confirmDownload() {
  confirming.value = false
  await downloadRouteForOffline(props.route)
}
</script>

<template>
  <section class="bg-white border border-gray-200 rounded-xl p-6">
    <div class="flex items-start justify-between gap-4">
      <div>
        <h3 class="text-lg font-semibold text-gray-900">{{ t('routesUi.offline.title') }}</h3>
        <p class="text-sm text-gray-600 mt-1">{{ t('routesUi.offline.description') }}</p>
      </div>
      <div class="flex flex-col items-end gap-2">
        <span
          v-if="saved"
          class="text-xs font-medium text-green-700 bg-green-50 border border-green-200 px-2 py-1 rounded-full"
        >
          {{ t('routesUi.offline.saved') }}
        </span>
      </div>
    </div>

    <!-- progress -->
    <div v-if="downloading" class="mt-4">
      <div class="h-2 w-full rounded-full bg-gray-100 overflow-hidden">
        <div class="h-full bg-primary-600 transition-all" :style="{ width: `${percent}%` }"></div>
      </div>
      <div class="text-xs text-gray-500 mt-1">{{ t('routesUi.offline.downloading', { percent }) }}</div>
    </div>

    <!-- confirm dialog -->
    <div v-else-if="confirming" class="mt-4 space-y-2">
      <p class="text-sm text-gray-700">{{ t('routesUi.offline.confirm', { count: tileEstimate }) }}</p>
      <div class="flex gap-2">
        <AppButton size="sm" @click="confirmDownload">{{ t('routesUi.offline.confirmDownload') }}</AppButton>
        <AppButton size="sm" variant="ghost" @click="confirming = false">{{ t('routesUi.close') }}</AppButton>
      </div>
    </div>

    <!-- actions -->
    <div v-else class="mt-4 flex items-center gap-3">
      <AppButton v-if="!saved" size="sm" :disabled="!online" @click="confirming = true">
        {{ t('routesUi.offline.download') }}
      </AppButton>
      <AppButton v-else size="sm" variant="ghost" @click="removeOfflineRoute(route.id)">
        {{ t('routesUi.offline.remove') }}
      </AppButton>
      <span v-if="!online && !saved" class="text-xs text-amber-600">{{ t('routesUi.offline.mustBeOnline') }}</span>
      <span v-if="savedEntry" class="text-xs text-gray-500">
        {{ t('routesUi.offline.tilesCached', { count: savedEntry.tiles }) }}
      </span>
    </div>
  </section>
</template>
