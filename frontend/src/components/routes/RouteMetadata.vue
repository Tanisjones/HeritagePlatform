<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import type { HeritageRoute } from '@/types/heritage'

const props = defineProps<{
  route: HeritageRoute
  compact?: boolean
}>()

const { t } = useI18n()

function formatDuration(value?: string | null) {
  if (!value) return null
  // DRF DurationField often returns "HH:MM:SS"
  const parts = value.split(':')
  if (parts.length !== 3) return value
  const h = parseInt(parts[0] ?? '', 10)
  const m = parseInt(parts[1] ?? '', 10)
  if (!Number.isFinite(h) || !Number.isFinite(m)) return value
  if (h > 0) return `${h}h ${m}m`
  return `${m}m`
}

function formatDistance(km?: number | null) {
  if (km === null || km === undefined) return null
  if (!Number.isFinite(km)) return null
  return `${km.toFixed(km >= 10 ? 0 : 1)} km`
}

function formatRating(r?: number | null) {
  if (r === null || r === undefined) return null
  if (!Number.isFinite(r)) return null
  return r.toFixed(1)
}

const durationLabel = formatDuration(props.route.estimated_duration ?? null)
const distanceLabel = formatDistance(props.route.distance ?? null)
const ratingLabel = formatRating(props.route.average_rating ?? null)

const difficultyLabel = computed(() => {
  const difficulty = props.route.difficulty
  if (!difficulty) return null
  const key = `routesUi.difficulty.${difficulty}` as const
  const translated = t(key)
  return translated === key ? difficulty : translated
})

const bestSeasonLabel = computed(() => {
  const bestSeason = props.route.best_season
  if (!bestSeason) return null
  const key = bestSeason === 'year_round' ? 'routesUi.bestSeason.yearRound' : `routesUi.bestSeason.${bestSeason}`
  const translated = t(key)
  return translated === key ? bestSeason : translated
})

const stopsLabel = computed(() => {
  if (props.route.stop_count === undefined) return null
  const count = props.route.stop_count
  const key = count === 1 ? 'routesUi.metadata.stop' : 'routesUi.metadata.stops'
  return t(key, { count })
})
</script>

<template>
  <div class="flex flex-wrap items-center gap-2 text-sm text-gray-600">
    <span v-if="route.difficulty" class="inline-flex items-center rounded-full bg-gray-100 px-2 py-0.5">
      {{ difficultyLabel }}
    </span>
    <span v-if="route.stop_count !== undefined" class="inline-flex items-center rounded-full bg-gray-100 px-2 py-0.5">
      {{ stopsLabel }}
    </span>
    <span v-if="distanceLabel" class="inline-flex items-center rounded-full bg-gray-100 px-2 py-0.5">
      {{ distanceLabel }}
    </span>
    <span v-if="durationLabel" class="inline-flex items-center rounded-full bg-gray-100 px-2 py-0.5">
      {{ durationLabel }}
    </span>
    <span v-if="route.wheelchair_accessible" class="inline-flex items-center rounded-full bg-green-50 text-green-700 px-2 py-0.5">
      {{ t('routesUi.metadata.wheelchair') }}
    </span>
    <span v-if="ratingLabel" class="inline-flex items-center rounded-full bg-yellow-50 text-yellow-800 px-2 py-0.5">
      ★ {{ ratingLabel }}
    </span>
    <span v-if="!compact && route.best_season" class="inline-flex items-center rounded-full bg-blue-50 text-blue-700 px-2 py-0.5">
      {{ bestSeasonLabel }}
    </span>
  </div>
</template>
