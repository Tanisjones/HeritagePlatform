<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import type { RouteStep } from '@/types/heritage'

/**
 * Turn-by-turn walking directions (from the OSRM routing provider). Hidden when
 * the route has no steps — e.g. the straight-line fallback, which produces none.
 */
const props = defineProps<{ steps?: RouteStep[] }>()

const { t } = useI18n()

const steps = computed(() => props.steps || [])

function formatDistance(m: number): string {
  if (m >= 1000) return `${(m / 1000).toFixed(1)} km`
  return `${Math.round(m)} m`
}

// Humanize an OSRM maneuver string like "turn left" into a translated label,
// falling back to the raw instruction (or the street name) when unknown.
function label(step: RouteStep): string {
  const raw = (step.instruction || '').trim()
  const key = `routesUi.directions.maneuvers.${raw.replace(/\s+/g, '_')}`
  const translated = t(key)
  const base = translated === key ? raw || step.name || t('routesUi.directions.continue') : translated
  return step.name ? `${base} · ${step.name}` : base
}
</script>

<template>
  <section v-if="steps.length" class="bg-white border border-gray-200 rounded-xl p-6">
    <h2 class="text-lg font-semibold text-gray-900 mb-1">{{ t('routesUi.directions.title') }}</h2>
    <p class="text-sm text-gray-600 mb-4">{{ t('routesUi.directions.subtitle') }}</p>
    <ol class="space-y-2">
      <li
        v-for="(step, idx) in steps"
        :key="idx"
        class="flex items-start gap-3 text-sm"
      >
        <span class="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-gray-100 text-gray-700 text-xs font-semibold">
          {{ idx + 1 }}
        </span>
        <span class="flex-1 text-gray-800">{{ label(step) }}</span>
        <span v-if="step.distance_m > 0" class="text-xs text-gray-500 whitespace-nowrap">
          {{ formatDistance(step.distance_m) }}
        </span>
      </li>
    </ol>
  </section>
</template>
