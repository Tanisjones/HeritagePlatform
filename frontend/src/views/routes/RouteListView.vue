<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRoutesStore } from '@/stores/routes'
import { useAuthStore } from '@/stores/auth'
import { useCityPath } from '@/composables/useCityPath'
import { useGeolocation } from '@/composables/useGeolocation'
import RouteFilters from '@/components/routes/RouteFilters.vue'
import RouteCard from '@/components/routes/RouteCard.vue'
import AppButton from '@/components/common/AppButton.vue'
import BaseSpinner from '@/components/common/BaseSpinner.vue'
import ErrorBanner from '@/components/common/ErrorBanner.vue'
import EmptyState from '@/components/common/EmptyState.vue'

const { t } = useI18n()
const routesStore = useRoutesStore()
const authStore = useAuthStore()
const { cityPath } = useCityPath()
const { lngLat, isSupported, error: geoError, start, stop } = useGeolocation()

const filters = ref<Record<string, any>>({})
const loading = computed(() => routesStore.loading)

// 'all' shows the filtered catalogue; 'nearby' shows geolocated results.
const mode = ref<'all' | 'nearby'>('all')
const locating = ref(false)
const nearbyError = ref('')

const displayedRoutes = computed(() =>
  mode.value === 'nearby' ? routesStore.nearbyRoutes : routesStore.routes,
)

async function load() {
  // The store re-throws so other callers can react; here the error surfaces via
  // routesStore.error in the template, so swallow to avoid an unhandled rejection.
  try {
    await routesStore.fetchRoutes(filters.value)
  } catch {
    /* shown via routesStore.error */
  }
}

function findNearby() {
  if (!isSupported.value) {
    nearbyError.value = t('routesUi.nearby.unsupported')
    return
  }
  nearbyError.value = ''
  locating.value = true
  start()

  // Resolve on the first fix, or bail on a geolocation error.
  const unwatch = watch([lngLat, geoError], async ([pos, err]) => {
    if (pos) {
      unwatch()
      stop()
      try {
        await routesStore.fetchNearbyRoutes({ latitude: pos[1], longitude: pos[0], radius: 5 })
        mode.value = 'nearby'
      } catch {
        nearbyError.value = t('routesUi.nearby.error')
      } finally {
        locating.value = false
      }
    } else if (err) {
      unwatch()
      stop()
      locating.value = false
      nearbyError.value = t('routesUi.nearby.denied')
    }
  })
}

function showAll() {
  mode.value = 'all'
  nearbyError.value = ''
}

onMounted(load)
</script>

<template>
  <div class="max-w-6xl mx-auto p-5 space-y-5">
    <div class="flex items-center justify-between gap-4">
      <h1 class="text-3xl font-bold text-gray-900">{{ t('routes.title') }}</h1>
      <div class="flex items-center gap-2">
        <AppButton size="sm" variant="secondary" :loading="locating" @click="findNearby">
          {{ t('routesUi.nearby.button') }}
        </AppButton>
        <router-link v-if="authStore.isAuthenticated" :to="cityPath('/routes/new')">
          <AppButton size="sm">{{ t('routesUi.createRoute') }}</AppButton>
        </router-link>
      </div>
    </div>

    <ErrorBanner :message="nearbyError" dense :retryable="false" />
    <ErrorBanner :message="mode === 'all' ? routesStore.error : null" dense @retry="load" />

    <!-- Nearby mode banner -->
    <div
      v-if="mode === 'nearby'"
      class="flex items-center justify-between gap-3 bg-primary-50 border border-primary-200 rounded-lg px-4 py-2"
    >
      <span class="text-sm text-primary-800">{{ t('routesUi.nearby.showing') }}</span>
      <button class="text-sm text-primary-700 hover:underline" @click="showAll">
        {{ t('routesUi.nearby.showAll') }}
      </button>
    </div>

    <RouteFilters
      v-if="mode === 'all'"
      @change="
        async (p) => {
          filters.value = p
          await load()
        }
      "
    />

    <div v-if="loading || locating" class="flex justify-center items-center py-12">
      <BaseSpinner class="h-8 w-8 text-primary-600" />
    </div>

    <div v-else-if="displayedRoutes.length > 0" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
      <RouteCard v-for="r in displayedRoutes" :key="r.id" :route="r" />
    </div>

    <EmptyState
      v-else
      :title="mode === 'nearby' ? t('routesUi.nearby.noneNear') : t('routes.noRoutes')"
    />
  </div>
</template>
