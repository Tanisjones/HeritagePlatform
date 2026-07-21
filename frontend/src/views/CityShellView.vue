<script setup lang="ts">
import { onUnmounted, ref, watch } from 'vue'
import { RouterView, useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useCityStore } from '@/stores/city'
import { slugForSegment } from '@/router/cityContext'
import { ALL_CITIES } from '@/services/api'
import NotFoundView from '@/views/NotFoundView.vue'
import BaseSpinner from '@/components/common/BaseSpinner.vue'
import ErrorBanner from '@/components/common/ErrorBanner.vue'

/**
 * CityShellView — parent of every /:citySlug route. Validates the slug
 * against the catalog ('all' → ALL_CITIES sentinel) and syncs it into the
 * city store (persist + X-City + SW cache purge) before children render, so
 * their first fetches carry the right scope. The keyed RouterView remounts
 * all views on cross-city navigation, which refetches everything.
 */
const { t } = useI18n()
const route = useRoute()
const cityStore = useCityStore()

type Status = 'loading' | 'ready' | 'unknown' | 'error'
const status = ref<Status>('loading')

// Only the newest run may commit: navigating A → B → A while the catalog
// request is in flight leaves three overlapping closures, and without this an
// older one could adopt its slug after the user has moved on.
let runId = 0

async function sync(segment: string, force = false) {
  const run = ++runId
  // Reset synchronously, BEFORE the first await. The keyed <RouterView> below
  // re-renders in the same flush as this watcher, so leaving the previous
  // 'ready' in place would remount children under the new slug while the
  // store still holds the old city — their first fetches would go out with
  // the wrong X-City and nothing would refetch afterwards.
  status.value = 'loading'

  await cityStore.load(force)
  if (run !== runId) return

  if (!cityStore.loaded || cityStore.cities.length === 0) {
    // No catalog to validate against. Refuse rather than adopt an unverified
    // slug: the API resolves an unknown X-City to "no city" and answers
    // unfiltered, which would render every city's content as if it were this
    // one.
    status.value = 'error'
    return
  }

  const slug = slugForSegment(segment)
  if (slug !== ALL_CITIES && !cityStore.cities.some((c) => c.slug === slug)) {
    status.value = 'unknown'
    return
  }

  await cityStore.adoptSlug(slug)
  if (run !== runId) return
  status.value = 'ready'
}

watch(
  () => route.params.citySlug,
  (segment) => {
    if (typeof segment !== 'string' || !segment) return
    void sync(segment)
  },
  { immediate: true }
)

// Leaving the city shell (to /dashboard, /moderation, /teach…) drops the
// URL scope, so those pages go back to the city the user actually chose
// instead of inheriting whichever one they last browsed.
onUnmounted(() => {
  runId++
  cityStore.releaseUrlCity()
})

function retry() {
  const segment = route.params.citySlug
  if (typeof segment === 'string' && segment) void sync(segment, true)
}
</script>

<template>
  <NotFoundView v-if="status === 'unknown'" />

  <div v-else-if="status === 'error'" class="max-w-lg mx-auto px-4 py-20">
    <ErrorBanner :message="t('cityShell.catalogError')" retryable @retry="retry" />
  </div>

  <div v-else-if="status === 'loading'" class="flex justify-center py-24" role="status">
    <BaseSpinner class="h-10 w-10 text-primary-600" />
    <span class="sr-only">{{ t('common.loading') }}</span>
  </div>

  <RouterView v-else :key="String(route.params.citySlug)" />
</template>
