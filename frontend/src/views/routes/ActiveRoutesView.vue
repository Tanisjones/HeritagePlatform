<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoutesStore } from '@/stores/routes'
import RouteCard from '@/components/routes/RouteCard.vue'
import BaseSpinner from '@/components/common/BaseSpinner.vue'

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
      <BaseSpinner class="h-8 w-8 text-primary-600" />
    </div>

    <div v-else-if="routes.length === 0" class="text-gray-600">{{ t('routesUi.states.noActiveRoutes') }}</div>

    <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
      <RouteCard v-for="r in routes" :key="r.id" :route="r" />
    </div>
  </div>
</template>
