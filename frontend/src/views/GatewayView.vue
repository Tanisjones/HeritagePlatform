<script setup lang="ts">
import { onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useCityStore } from '@/stores/city'
import BaseSpinner from '@/components/common/BaseSpinner.vue'
import ErrorBanner from '@/components/common/ErrorBanner.vue'

/**
 * GatewayView — the platform front page at `/`. A minimal presentation of the
 * platform with one card per city linking to its landing (`/<slug>`), plus a
 * secondary link to the cross-city explore mode (`/all/explore`). Rendered
 * with the platform-default theme (App.vue clears any city palette here).
 *
 * This is the app's front door and the PWA start_url, so a failed catalog
 * fetch must never leave it as a bare spinner: it degrades to an error with a
 * retry, and the cross-city escape link stays available either way.
 */
const { t } = useI18n()
const cityStore = useCityStore()

onMounted(() => {
  cityStore.load()
})
</script>

<template>
  <div class="min-h-[calc(100vh-4rem)] bg-gradient-to-b from-primary-50 via-white to-white">
    <div class="max-w-5xl mx-auto px-4 py-14 md:py-20">
      <div class="text-center">
        <h1 class="font-display text-4xl md:text-5xl font-bold text-gray-900">
          {{ t('common.brand') }}
        </h1>
        <p class="mt-4 text-lg text-gray-600 max-w-2xl mx-auto">
          {{ t('gateway.tagline') }}
        </p>
      </div>

      <div v-if="cityStore.loadError" class="mt-10">
        <ErrorBanner
          :message="t('gateway.loadError')"
          retryable
          @retry="cityStore.load(true)"
        />
      </div>

      <div v-else-if="!cityStore.loaded" class="flex justify-center py-16" role="status">
        <BaseSpinner class="h-10 w-10 text-primary-600" />
        <span class="sr-only">{{ t('gateway.loading') }}</span>
      </div>

      <div v-else class="grid grid-cols-1 sm:grid-cols-2 gap-5 mt-10 md:mt-14">
        <RouterLink
          v-for="city in cityStore.cities"
          :key="city.slug"
          :to="`/${city.slug}`"
          class="relative h-48 md:h-56 rounded-2xl overflow-hidden group border border-gray-200 shadow-sm hover:shadow-lg focus:outline-none focus:ring-2 focus:ring-primary-600 transition-shadow"
        >
          <div
            class="absolute inset-0 bg-cover bg-center transition-transform duration-300 group-hover:scale-105"
            :class="{ 'bg-gradient-to-br from-primary-400 to-primary-700': !city.hero_image }"
            :style="city.hero_image ? { backgroundImage: `url('${city.hero_image}')` } : {}"
          ></div>
          <div class="absolute inset-0 bg-gradient-to-t from-black/70 via-black/20 to-transparent"></div>
          <div class="absolute bottom-0 left-0 right-0 p-5 flex items-end justify-between gap-3">
            <div>
              <div class="text-white text-xl md:text-2xl font-bold">{{ city.name }}</div>
              <div class="text-white/80 text-sm">
                {{ [city.region, city.country_name].filter(Boolean).join(', ') }}
              </div>
            </div>
            <span
              class="shrink-0 text-white/90 text-sm font-medium opacity-0 group-hover:opacity-100 transition-opacity"
              aria-hidden="true"
            >
              →
            </span>
          </div>
        </RouterLink>
      </div>

      <!-- Always available: the one escape hatch that needs no catalog. -->
      <div v-if="cityStore.loaded || cityStore.loadError" class="text-center mt-10">
        <RouterLink
          to="/all/explore"
          class="text-sm font-medium text-primary-700 hover:text-primary-900 underline"
        >
          {{ t('gateway.exploreAll') }}
        </RouterLink>
      </div>
    </div>
  </div>
</template>
