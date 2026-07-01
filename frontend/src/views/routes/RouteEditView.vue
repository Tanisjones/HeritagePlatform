<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '@/stores/auth'
import { useRoutesStore } from '@/stores/routes'
import RouteForm from '@/components/routes/RouteForm.vue'
import BaseSpinner from '@/components/common/BaseSpinner.vue'
import type { RouteCreateData } from '@/types/heritage'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const routesStore = useRoutesStore()
const { t } = useI18n()

const routeId = computed(() => String(route.params.id || ''))
const loading = ref(true)
const initial = ref<Partial<RouteCreateData> | null>(null)
const forbidden = ref(false)

onMounted(async () => {
  let loaded
  try {
    // fetchRoute re-throws on failure (store uses rethrow), so a 404/network
    // error would otherwise leave `loading` stuck true; catch it and fall
    // through to the "route not found" branch (initial stays null).
    loaded = await routesStore.fetchRoute(routeId.value)
  } catch {
    loading.value = false
    return
  }
  if (!loaded) {
    loading.value = false
    return
  }
  // Only the creator may edit.
  if (loaded.creator?.id && authStore.user?.id && loaded.creator.id !== authStore.user.id) {
    forbidden.value = true
    loading.value = false
    return
  }
  initial.value = {
    title: loaded.title,
    description: loaded.description,
    theme: loaded.theme,
    theme_category: loaded.theme_category ?? undefined,
    difficulty: loaded.difficulty,
    estimated_duration: loaded.estimated_duration ?? undefined,
    distance: loaded.distance ?? undefined,
    wheelchair_accessible: loaded.wheelchair_accessible,
    public_transit_accessible: loaded.public_transit_accessible,
    accessibility_notes: loaded.accessibility_notes,
    best_season: loaded.best_season,
    estimated_cost: loaded.estimated_cost ?? undefined,
    cost_notes: loaded.cost_notes,
    available_languages: loaded.available_languages,
    stops: (loaded.stops || []).map((s) => ({
      id: s.id,
      heritage_item_id: s.heritage_item.id,
      order: s.order,
      arrival_instructions: s.arrival_instructions,
      suggested_time: s.suggested_time,
      location: s.heritage_item.location,
      title: s.heritage_item.title,
    })),
  }
  loading.value = false
})

async function onSubmit(payload: RouteCreateData) {
  await routesStore.updateRoute(routeId.value, payload)
  router.push({ name: 'route-detail', params: { id: routeId.value } })
}
</script>

<template>
  <div class="max-w-4xl mx-auto p-5">
    <h1 class="text-3xl font-bold text-gray-900 mb-6">{{ t('routesUi.builder.editRouteTitle') }}</h1>

    <div v-if="loading" class="flex justify-center py-12">
      <BaseSpinner class="h-8 w-8 text-primary-600" />
    </div>
    <div v-else-if="forbidden" class="text-center py-12 text-gray-600">
      {{ t('routesUi.builder.notAllowedToEdit') }}
    </div>
    <RouteForm v-else-if="initial" :initial="initial" :loading="routesStore.loading" @submit="onSubmit" />
    <div v-else class="text-center py-12 text-gray-600">{{ t('routesUi.states.routeNotFound') }}</div>
  </div>
</template>
