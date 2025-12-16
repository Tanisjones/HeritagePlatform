<script setup lang="ts">
import { useRouter } from 'vue-router'
import { useRoutesStore } from '@/stores/routes'
import RouteForm from '@/components/routes/RouteForm.vue'
import type { RouteCreateData } from '@/types/heritage'
import { useI18n } from 'vue-i18n'

const router = useRouter()
const routesStore = useRoutesStore()
const { t } = useI18n()

async function onSubmit(payload: RouteCreateData) {
  const created = await routesStore.createRoute(payload)
  router.push({ name: 'route-detail', params: { id: created.id } })
}
</script>

<template>
  <div class="max-w-4xl mx-auto p-5">
    <h1 class="text-3xl font-bold text-gray-900 mb-6">{{ t('routesUi.pages.createRouteTitle') }}</h1>
    <RouteForm :loading="routesStore.loading" @submit="onSubmit" />
  </div>
</template>
