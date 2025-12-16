<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoutesStore } from '@/stores/routes'
import RouteCard from '@/components/routes/RouteCard.vue'
import AppButton from '@/components/common/AppButton.vue'

const { t } = useI18n()
const routesStore = useRoutesStore()
const loading = computed(() => routesStore.loading)
const routes = computed(() => routesStore.myRoutes)

async function load() {
  await routesStore.fetchMyRoutes()
}

async function submitForReview(id: string) {
  await routesStore.submitForReview(id)
  await routesStore.fetchMyRoutes()
}

onMounted(load)
</script>

<template>
  <div class="max-w-6xl mx-auto p-5 space-y-5">
    <div class="flex items-center justify-between gap-4">
      <h1 class="text-3xl font-bold text-gray-900">{{ t('routesUi.pages.myRoutesTitle') }}</h1>
      <router-link to="/routes/new">
        <AppButton size="sm">{{ t('routesUi.createRoute') }}</AppButton>
      </router-link>
    </div>

    <div v-if="loading" class="flex justify-center items-center py-12">
      <svg class="animate-spin h-8 w-8 text-primary-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
      </svg>
    </div>

    <div v-else-if="routes.length === 0" class="text-gray-600">{{ t('routesUi.states.noRoutesYet') }}</div>

    <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
      <div v-for="r in routes" :key="r.id" class="space-y-2">
        <RouteCard :route="r" />
        <div v-if="r.status === 'draft' || r.status === 'changes_requested'" class="flex justify-end">
          <AppButton size="sm" variant="secondary" :loading="loading" @click="submitForReview(r.id)">
            {{ t('routesUi.actions.submitForReview') }}
          </AppButton>
        </div>
      </div>
    </div>
  </div>
</template>
