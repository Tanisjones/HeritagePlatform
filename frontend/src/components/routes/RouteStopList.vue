<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { RouterLink } from 'vue-router'
import type { RouteStop } from '@/types/heritage'

const { t } = useI18n()

defineProps<{
  stops: RouteStop[]
  visitedStopIds?: Set<string>
}>()
</script>

<template>
  <ol class="space-y-3">
    <li
      v-for="stop in stops"
      :key="stop.id"
      class="border border-gray-200 rounded-xl p-4 flex items-start gap-3"
    >
      <div
        class="flex h-8 w-8 items-center justify-center rounded-full text-sm font-semibold"
        :class="visitedStopIds?.has(stop.id) ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-700'"
      >
        {{ stop.order }}
      </div>
      <div class="flex-1">
        <RouterLink
          :to="{ name: 'heritage-detail', params: { id: stop.heritage_item.id } }"
          class="text-gray-900 font-medium hover:text-primary-700"
        >
          {{ stop.heritage_item.title }}
        </RouterLink>
        <div v-if="stop.arrival_instructions" class="text-sm text-gray-600 mt-1">
          {{ stop.arrival_instructions }}
        </div>
        <div v-if="stop.suggested_time" class="text-xs text-gray-500 mt-1">
          {{ t('routesUi.stop.suggestedTime', { time: stop.suggested_time }) }}
        </div>
      </div>
    </li>
  </ol>
</template>
