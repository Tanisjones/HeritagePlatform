<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '@/stores/auth'
import { useRoutesStore } from '@/stores/routes'
import { useRouteNavigation } from '@/composables/useRouteNavigation'
import { routeService } from '@/services/api'
import { saveBlob, readBlobError, slugifyFilename } from '@/utils/download'
import AppButton from '@/components/common/AppButton.vue'
import RouteStopList from '@/components/routes/RouteStopList.vue'
import RouteMetadata from '@/components/routes/RouteMetadata.vue'
import RouteRating from '@/components/routes/RouteRating.vue'
import RouteProgressTracker from '@/components/routes/RouteProgressTracker.vue'
import RouteMap from '@/components/routes/RouteMap.vue'
import RouteDirections from '@/components/routes/RouteDirections.vue'
import RouteAudioGuide from '@/components/routes/RouteAudioGuide.vue'
import RouteCard from '@/components/routes/RouteCard.vue'
import OfflineRouteManager from '@/components/routes/OfflineRouteManager.vue'
import BaseSpinner from '@/components/common/BaseSpinner.vue'
import type { HeritageRoute } from '@/types/heritage'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const routesStore = useRoutesStore()
const { t } = useI18n()

const loading = computed(() => routesStore.loading)
const currentRoute = computed(() => routesStore.currentRoute)
const routeId = computed(() => String(route.params.id || ''))

const isCreator = computed(
  () => !!currentRoute.value?.creator?.id && currentRoute.value.creator.id === authStore.user?.id,
)

const visitedStopIds = computed(() => {
  const visited = currentRoute.value?.user_progress?.visited_stops || []
  return new Set(visited.map((s) => s.id))
})

// --- On-the-ground navigation (geolocation + auto check-in) ---
const nav = useRouteNavigation(currentRoute, (stopId, coords) =>
  routesStore.checkInAtStop(routeId.value, stopId, coords),
)

// Guided walk: the audioguide follows the stop the user is AT (current_stop,
// set on check-in); before the first check-in it previews the next stop.
const audioGuideStop = computed(
  () => currentRoute.value?.user_progress?.current_stop || nav.nextStop.value,
)

// --- Completion + gamification toast ---
const showCompleted = ref(false)
const earnedPoints = ref(0)
const earnedBadges = ref<string[]>([])

// --- Exports / errors ---
const exportError = ref<string | null>(null)
const exporting = ref(false)
const actionError = ref<string | null>(null)

// --- Similar routes ---
const similarRoutes = ref<HeritageRoute[]>([])

async function load() {
  await routesStore.fetchRoute(routeId.value)
  similarRoutes.value = await routesStore.fetchSimilarRoutes(routeId.value)
}

async function onStart() {
  await routesStore.startRoute(routeId.value)
}

async function onComplete() {
  // The backend returns exactly what completing awarded (points delta + new
  // badge names), computed from the gamification it granted server-side.
  const { awards } = await routesStore.completeRoute(routeId.value)
  earnedPoints.value = awards.points
  earnedBadges.value = awards.badges
  showCompleted.value = true
}

async function onCheckIn(stopId: string) {
  const pos = nav.lngLat.value
  await routesStore.checkInAtStop(
    routeId.value,
    stopId,
    pos ? { latitude: pos[1], longitude: pos[0] } : undefined,
  )
}

async function onSkip(stopId: string) {
  await routesStore.skipStop(routeId.value, stopId)
}

// --- exports ---
async function exportRoute(kind: 'gpx' | 'kml') {
  if (!currentRoute.value) return
  exportError.value = null
  exporting.value = true
  try {
    const res = kind === 'gpx'
      ? await routeService.exportGpx(routeId.value)
      : await routeService.exportKml(routeId.value)
    saveBlob(res.data as Blob, `${slugifyFilename(currentRoute.value.title, 'route')}.${kind}`)
  } catch (e: any) {
    exportError.value = await readBlobError(e, t('routesUi.exports.error'))
  } finally {
    exporting.value = false
  }
}

// --- governance (creator) ---
async function onEdit() {
  router.push({ name: 'route-edit', params: { id: routeId.value } })
}

async function onDelete() {
  if (!window.confirm(t('routesUi.builder.confirmDelete'))) return
  actionError.value = null
  try {
    await routesStore.deleteRoute(routeId.value)
    router.push('/routes/my')
  } catch {
    actionError.value = t('routesUi.builder.deleteError')
  }
}

async function onArchive() {
  if (!window.confirm(t('routesUi.builder.confirmArchive'))) return
  actionError.value = null
  try {
    await routesStore.archiveRoute(routeId.value)
  } catch {
    actionError.value = t('routesUi.builder.archiveError')
  }
}

// --- share ---
async function onShare() {
  const url = window.location.href
  const title = currentRoute.value?.title || t('routes.title')
  try {
    if (navigator.share) {
      await navigator.share({ title, text: title, url })
    } else if (navigator.clipboard) {
      await navigator.clipboard.writeText(url)
    }
  } catch {
    /* user cancelled share */
  }
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

    <div v-if="loading && !currentRoute" class="flex justify-center items-center py-12">
      <BaseSpinner class="h-8 w-8 text-primary-600" />
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

        <!-- toolbar: export / share / creator actions -->
        <div class="mt-5 pt-4 border-t border-gray-100 flex flex-wrap items-center gap-2">
          <AppButton size="sm" variant="ghost" :loading="exporting" @click="exportRoute('gpx')">{{ t('routesUi.exports.gpx') }}</AppButton>
          <AppButton size="sm" variant="ghost" :loading="exporting" @click="exportRoute('kml')">{{ t('routesUi.exports.kml') }}</AppButton>
          <AppButton size="sm" variant="ghost" @click="onShare">{{ t('routesUi.actions.share') }}</AppButton>
          <span class="flex-1"></span>
          <template v-if="isCreator">
            <AppButton size="sm" variant="ghost" @click="onEdit">{{ t('routesUi.builder.edit') }}</AppButton>
            <AppButton
              v-if="['published', 'rejected'].includes(currentRoute.status || '')"
              size="sm" variant="ghost" @click="onArchive"
            >{{ t('routesUi.actions.archive') }}</AppButton>
            <button class="text-sm text-red-600 hover:text-red-700 px-2" @click="onDelete">{{ t('routesUi.builder.delete') }}</button>
          </template>
        </div>
        <p v-if="exportError" class="text-sm text-red-700 mt-2">{{ exportError }}</p>
        <p v-if="actionError" class="text-sm text-red-700 mt-2">{{ actionError }}</p>
      </section>

      <section class="bg-white border border-gray-200 rounded-xl overflow-hidden">
        <div class="px-6 py-4 border-b border-gray-200 flex items-center justify-between gap-4">
          <div>
            <h2 class="text-lg font-semibold text-gray-900">{{ t('routesUi.mapTitle') }}</h2>
            <p class="text-sm text-gray-600">{{ t('routesUi.mapSubtitle') }}</p>
          </div>
          <AppButton
            v-if="nav.isSupported.value && currentRoute.user_progress && !currentRoute.user_progress.completed_at"
            size="sm"
            :variant="nav.following.value ? 'secondary' : 'ghost'"
            @click="nav.following.value ? nav.stopFollowing() : nav.startFollowing()"
          >
            {{ nav.following.value ? t('routesUi.nav.stopFollowing') : t('routesUi.nav.followMe') }}
          </AppButton>
        </div>
        <div style="height: 420px" class="p-4">
          <RouteMap :route="currentRoute" :live-position="nav.lngLat.value" />
        </div>
        <div v-if="nav.following.value && nav.distanceToNext.value !== null" class="px-6 pb-4 text-sm text-gray-600">
          {{ t('routesUi.nav.distanceToNext', { meters: Math.round(nav.distanceToNext.value) }) }}
        </div>
      </section>

      <RouteDirections :steps="currentRoute.turn_by_turn" />

      <RouteAudioGuide
        v-if="currentRoute.user_progress && !currentRoute.user_progress.completed_at"
        :stop="audioGuideStop"
        :autoplay="true"
      />

      <RouteProgressTracker
        v-if="authStore.isAuthenticated && currentRoute.user_progress && !currentRoute.user_progress.completed_at"
        :stops="currentRoute.stops || []"
        :progress="currentRoute.user_progress"
        :loading="loading"
        @check-in="onCheckIn"
        @skip="onSkip"
      />

      <OfflineRouteManager v-if="currentRoute.status === 'published'" :route="currentRoute" />

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

      <!-- Similar routes -->
      <section v-if="similarRoutes.length" class="space-y-3">
        <h2 class="text-xl font-bold text-gray-900">{{ t('routesUi.similar.title') }}</h2>
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          <RouteCard v-for="r in similarRoutes" :key="r.id" :route="r" />
        </div>
      </section>
    </div>

    <div v-else class="text-center py-12">
      <p class="text-gray-600">{{ t('routesUi.states.routeNotFound') }}</p>
    </div>
  </div>

  <!-- Completion + gamification toast -->
  <div
    v-if="showCompleted"
    class="fixed inset-0 bg-black/40 flex items-center justify-center p-4 z-50"
    @click.self="showCompleted = false"
  >
    <div class="bg-white rounded-xl shadow-xl max-w-md w-full p-6 text-center">
      <div class="text-4xl mb-2">🎉</div>
      <h3 class="text-xl font-semibold text-gray-900">{{ t('routesUi.congratsTitle') }}</h3>
      <p class="text-gray-700 mt-2">{{ t('routesUi.congratsBody') }}</p>

      <div v-if="earnedPoints > 0" class="mt-4 text-2xl font-bold text-primary-600 route-award-pop">
        {{ t('routesUi.gamification.pointsEarned', { points: earnedPoints }) }}
      </div>
      <div v-if="earnedBadges.length" class="mt-3 flex flex-wrap justify-center gap-2">
        <span
          v-for="name in earnedBadges"
          :key="name"
          class="inline-flex items-center gap-1 text-sm font-medium text-amber-800 bg-amber-50 border border-amber-200 px-3 py-1 rounded-full route-award-pop"
        >
          🏅 {{ t('routesUi.gamification.newBadge', { name }) }}
        </span>
      </div>

      <div class="mt-6 flex justify-center gap-2">
        <AppButton variant="ghost" @click="showCompleted = false">{{ t('routesUi.close') }}</AppButton>
      </div>
    </div>
  </div>
</template>

<style scoped>
.route-award-pop {
  animation: award-pop 0.4s ease-out;
}
@keyframes award-pop {
  0% { transform: scale(0.6); opacity: 0; }
  70% { transform: scale(1.1); }
  100% { transform: scale(1); opacity: 1; }
}
</style>
