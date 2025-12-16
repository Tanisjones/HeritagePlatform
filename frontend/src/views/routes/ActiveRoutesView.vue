<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoutesStore } from '@/stores/routes'
import RouteCard from '@/components/routes/RouteCard.vue'

const { t } = useI18n()
const routesStore = useRoutesStore()
const loading = computed(() => routesStore.loading)
const routes = computed(() => routesStore.activeRoutes)

async function load() {
  await routesStore.fetchActiveRoutes()
}

onMounted(load)
</script>

<template>
  <div class="max-w-6xl mx-auto p-5 space-y-5">
    <h1 class="text-3xl font-bold text-gray-900">{{ t('routesUi.pages.activeRoutesTitle') }}</h1>

    <div v-if="loading" class="flex justify-center items-center py-12">
      <svg class="animate-spin h-8 w-8 text-primary-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
      </svg>
    </div>

    <div v-else-if="routes.length === 0" class="text-gray-600">{{ t('routesUi.states.noActiveRoutes') }}</div>

    <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
      <RouteCard v-for="r in routes" :key="r.id" :route="r" />
    </div>
  </div>
</template>
