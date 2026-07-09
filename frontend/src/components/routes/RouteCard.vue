<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { RouterLink } from 'vue-router'
import type { HeritageRoute } from '@/types/heritage'
import { useCityStore } from '@/stores/city'
import AppCard from '@/components/common/AppCard.vue'
import RouteMetadata from '@/components/routes/RouteMetadata.vue'

const props = defineProps<{
  route: HeritageRoute
}>()

const { t } = useI18n()
const cityStore = useCityStore()

const statusLabel = computed(() => {
  const status = props.route.status
  if (!status) return null
  const key = `routesUi.status.${status}` as const
  const translated = t(key)
  return translated === key ? status : translated
})

// C6 — curated theme chip: prefer the RouteTheme catalog entry (with its
// color) and fall back to the free-text theme string.
const themeChip = computed(() => {
  const detail = props.route.theme_category_detail
  if (detail?.name) return { label: detail.name, color: detail.color || null }
  if (props.route.theme) return { label: props.route.theme, color: null }
  return null
})
</script>

<template>
  <AppCard hoverable padding="lg">
    <RouterLink :to="{ name: 'route-detail', params: { id: route.id } }" class="block">
      <div class="flex items-start justify-between gap-3">
        <h3 class="text-lg font-semibold text-gray-900 group-hover:text-primary-700">
          {{ route.title }}
        </h3>
        <span
          v-if="route.status && route.status !== 'published'"
          class="text-xs rounded-full bg-gray-100 px-2 py-0.5 text-gray-700"
        >
          {{ statusLabel }}
        </span>
      </div>
      <div v-if="themeChip || (cityStore.isAllCities && route.city)" class="mt-2 flex flex-wrap gap-2">
        <span
          v-if="themeChip"
          class="text-xs rounded-full px-2 py-0.5 font-medium"
          :class="themeChip.color ? '' : 'bg-primary-100 text-primary-800'"
          :style="themeChip.color ? { backgroundColor: `${themeChip.color}22`, color: themeChip.color } : {}"
        >
          {{ themeChip.label }}
        </span>
        <!-- C1: city badge in the unscoped all-cities mode -->
        <span
          v-if="cityStore.isAllCities && route.city"
          class="text-xs rounded-full bg-secondary-100 text-secondary-800 px-2 py-0.5 font-medium"
        >
          {{ route.city.name }}
        </span>
      </div>
      <p class="mt-2 text-gray-600 line-clamp-3">
        {{ route.description }}
      </p>
      <div class="mt-4">
        <RouteMetadata :route="route" compact />
      </div>
    </RouterLink>
  </AppCard>
</template>
