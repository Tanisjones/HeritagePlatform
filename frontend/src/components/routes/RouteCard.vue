<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { RouterLink } from 'vue-router'
import type { HeritageRoute } from '@/types/heritage'
import AppCard from '@/components/common/AppCard.vue'
import RouteMetadata from '@/components/routes/RouteMetadata.vue'

const props = defineProps<{
  route: HeritageRoute
}>()

const { t } = useI18n()

const statusLabel = computed(() => {
  const status = props.route.status
  if (!status) return null
  const key = `routesUi.status.${status}` as const
  const translated = t(key)
  return translated === key ? status : translated
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
      <p class="mt-2 text-gray-600 line-clamp-3">
        {{ route.description }}
      </p>
      <div class="mt-4">
        <RouteMetadata :route="route" compact />
      </div>
    </RouterLink>
  </AppCard>
</template>
