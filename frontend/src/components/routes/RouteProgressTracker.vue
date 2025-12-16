<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import AppButton from '@/components/common/AppButton.vue'
import type { RouteStop, UserRouteProgress } from '@/types/heritage'

const { t } = useI18n()

const props = defineProps<{
  stops: RouteStop[]
  progress: UserRouteProgress
  loading?: boolean
}>()

const emit = defineEmits<{
  checkIn: [stopId: string]
  skip: [stopId: string]
}>()

const visitedIds = computed(() => new Set((props.progress.visited_stops || []).map((s) => s.id)))

const total = computed(() => props.stops.length)
const visitedCount = computed(() => (props.progress.visited_stops || []).length)
const percent = computed(() => (total.value ? Math.round((visitedCount.value / total.value) * 100) : 0))

const nextStop = computed(() => props.stops.find((s) => !visitedIds.value.has(s.id)) || null)

const startedAtLabel = computed(() => {
  const v = props.progress.started_at
  if (!v) return null
  return v.slice(0, 19).replace('T', ' ')
})
</script>

<template>
  <section class="bg-white border border-gray-200 rounded-xl p-6">
    <div class="flex items-start justify-between gap-4">
      <div class="flex-1">
        <h3 class="text-lg font-semibold text-gray-900">{{ t('routesUi.progress.title') }}</h3>
        <div class="text-sm text-gray-600 mt-1">
          {{ t('routesUi.progress.visitedSummary', { visited: visitedCount, total, percent }) }}
        </div>
        <div v-if="startedAtLabel" class="text-xs text-gray-500 mt-1">
          {{ t('routesUi.progress.started', { startedAt: startedAtLabel }) }}
        </div>
        <div class="mt-3 h-2 w-full rounded-full bg-gray-100 overflow-hidden">
          <div class="h-full bg-primary-600" :style="{ width: `${percent}%` }"></div>
        </div>
        <div v-if="nextStop" class="mt-3 text-sm text-gray-700">
          {{ t('routesUi.progress.next', { title: nextStop.heritage_item.title }) }}
        </div>
        <div v-else class="mt-3 text-sm text-gray-700">
          {{ t('routesUi.progress.allVisited') }}
        </div>
      </div>
      <div v-if="nextStop" class="flex flex-col gap-2">
        <AppButton size="sm" :loading="loading" @click="emit('checkIn', nextStop.id)">{{ t('routesUi.actions.checkIn') }}</AppButton>
        <AppButton size="sm" variant="ghost" :loading="loading" @click="emit('skip', nextStop.id)">{{ t('routesUi.actions.skip') }}</AppButton>
      </div>
    </div>
  </section>
</template>
