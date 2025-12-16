<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useRoutesStore } from '@/stores/routes'
import AppButton from '@/components/common/AppButton.vue'
import RouteStopList from '@/components/routes/RouteStopList.vue'
import RouteMetadata from '@/components/routes/RouteMetadata.vue'
import RouteRating from '@/components/routes/RouteRating.vue'
import RouteProgressTracker from '@/components/routes/RouteProgressTracker.vue'
import RouteMap from '@/components/routes/RouteMap.vue'
import { useI18n } from 'vue-i18n'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const routesStore = useRoutesStore()
const { t } = useI18n()

const loading = computed(() => routesStore.loading)
const currentRoute = computed(() => routesStore.currentRoute)

const routeId = computed(() => String(route.params.id || ''))

const visitedStopIds = computed(() => {
  const visited = currentRoute.value?.user_progress?.visited_stops || []
  return new Set(visited.map((s) => s.id))
})

const showCompleted = ref(false)

async function load() {
  await routesStore.fetchRoute(routeId.value)
}

async function onStart() {
  await routesStore.startRoute(routeId.value)
}

async function onComplete() {
  await routesStore.completeRoute(routeId.value)
  showCompleted.value = true
}

async function onCheckIn(stopId: string) {
  await routesStore.checkInAtStop(routeId.value, stopId)
}

async function onSkip(stopId: string) {
  await routesStore.skipStop(routeId.value, stopId)
}

onMounted(load)
</script>

<template>
  <div class="max-w-5xl mx-auto p-5 space-y-5">
    <div class="flex items-center justify-between gap-4">
      <button class="text-sm text-gray-600 hover:text-primary-700" @click="router.back()">← {{ t('routesUi.nav.back') }}</button>
      <div v-if="authStore.isAuthenticated" class="flex items-center gap-2">
        <router-link to="/routes/my" class="text-sm text-gray-600 hover:text-primary-700">{{ t('routesUi.nav.myRoutes') }}</router-link>
        <span class="text-gray-300">•</span>
        <router-link to="/routes/active" class="text-sm text-gray-600 hover:text-primary-700">{{ t('routesUi.nav.active') }}</router-link>
      </div>
    </div>

    <div v-if="loading" class="flex justify-center items-center py-12">
      <svg class="animate-spin h-8 w-8 text-primary-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
      </svg>
    </div>

    <div v-else-if="currentRoute" class="space-y-5">
      <section class="bg-white border border-gray-200 rounded-xl p-6">
        <div class="flex items-start justify-between gap-4">
          <div>
            <h1 class="text-3xl font-bold text-gray-900">{{ currentRoute.title }}</h1>
            <p class="text-gray-700 leading-relaxed mt-3">{{ currentRoute.description }}</p>
            <div class="mt-4">
              <RouteMetadata :route="currentRoute" />
            </div>
          </div>
          <div v-if="authStore.isAuthenticated" class="flex flex-col gap-2">
            <AppButton
              v-if="currentRoute.status === 'published' && !currentRoute.user_progress?.completed_at"
              :disabled="!!currentRoute.user_progress"
              :loading="loading"
              @click="onStart"
            >
              {{ currentRoute.user_progress ? t('routesUi.actions.inProgress') : t('routesUi.actions.startRoute') }}
            </AppButton>
            <AppButton
              v-if="currentRoute.user_progress && !currentRoute.user_progress.completed_at"
              variant="secondary"
              :loading="loading"
              @click="onComplete"
            >
              {{ t('routesUi.actions.complete') }}
            </AppButton>
          </div>
        </div>
      </section>

      <section class="bg-white border border-gray-200 rounded-xl overflow-hidden">
        <div class="px-6 py-4 border-b border-gray-200">
          <h2 class="text-lg font-semibold text-gray-900">{{ t('routesUi.mapTitle') }}</h2>
          <p class="text-sm text-gray-600">{{ t('routesUi.mapSubtitle') }}</p>
        </div>
        <div style="height: 420px" class="p-4">
          <RouteMap :route="currentRoute" />
        </div>
      </section>

      <RouteProgressTracker
        v-if="authStore.isAuthenticated && currentRoute.user_progress && !currentRoute.user_progress.completed_at"
        :stops="currentRoute.stops || []"
        :progress="currentRoute.user_progress"
        :loading="loading"
        @check-in="onCheckIn"
        @skip="onSkip"
      />

      <section class="bg-white border border-gray-200 rounded-xl p-6">
        <h2 class="text-2xl font-bold text-gray-900 mb-4">{{ t('routesUi.stopsTitle') }}</h2>
        <div v-if="(currentRoute.stops || []).length === 0" class="text-gray-600">{{ t('routesUi.states.noStopsYet') }}</div>
        <RouteStopList v-else :stops="currentRoute.stops || []" :visited-stop-ids="visitedStopIds" />
      </section>

      <section
        v-if="authStore.isAuthenticated && currentRoute.user_progress?.completed_at"
        class="bg-green-50 border border-green-200 rounded-xl p-6"
      >
        <div class="flex items-start justify-between gap-4">
          <div>
            <h3 class="text-lg font-semibold text-green-900">{{ t('routesUi.routeCompletedTitle') }}</h3>
            <div class="text-sm text-green-800 mt-1">
              {{
                t('routesUi.detail.completedAt', {
                  datetime: currentRoute.user_progress.completed_at.slice(0, 19).replace('T', ' '),
                })
              }}
            </div>
          </div>
          <AppButton
            v-if="currentRoute.status === 'published'"
            variant="secondary"
            :loading="loading"
            @click="onStart"
          >
            {{ t('routesUi.actions.startAgain') }}
          </AppButton>
        </div>
      </section>

      <RouteRating
        v-if="authStore.isAuthenticated && currentRoute.status === 'published'"
        :initial-rating="currentRoute.user_rating?.rating ?? null"
        :initial-comment="currentRoute.user_rating?.comment || ''"
        :loading="loading"
        @submit="(p) => routesStore.rateRoute(routeId, p)"
      />
    </div>

    <div v-else class="text-center py-12">
      <p class="text-gray-600">{{ t('routesUi.states.routeNotFound') }}</p>
    </div>
  </div>

  <div
    v-if="showCompleted"
    class="fixed inset-0 bg-black/40 flex items-center justify-center p-4 z-50"
    @click.self="showCompleted = false"
  >
    <div class="bg-white rounded-xl shadow-xl max-w-md w-full p-6">
      <h3 class="text-xl font-semibold text-gray-900">{{ t('routesUi.congratsTitle') }}</h3>
      <p class="text-gray-700 mt-2">{{ t('routesUi.congratsBody') }}</p>
      <div class="mt-5 flex justify-end gap-2">
        <AppButton variant="ghost" @click="showCompleted = false">{{ t('routesUi.close') }}</AppButton>
        <AppButton variant="secondary" @click="showCompleted = false">{{ t('routesUi.actions.viewStops') }}</AppButton>
      </div>
    </div>
  </div>
</template>
