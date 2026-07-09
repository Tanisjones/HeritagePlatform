<script setup lang="ts">
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useCityStore } from '@/stores/city'
import { ALL_CITIES } from '@/services/api'

/**
 * CityPickerSplash (C2) — one-time "¿Qué ciudad quieres explorar?" overlay for
 * brand-new visitors on a multi-city deployment. Shows exactly once by
 * construction: it only renders when nothing was persisted in hp_city before
 * this session (cityStore.firstVisit), and the catalog load persists a default
 * immediately, so the next visit never qualifies. Picking a city goes through
 * the normal setCity flow (persist + reload); "seguir con la actual" or the
 * backdrop just dismisses.
 */
const { t } = useI18n()
const cityStore = useCityStore()
const dismissed = ref(false)

const visible = computed(
  () =>
    !dismissed.value &&
    cityStore.firstVisit &&
    cityStore.loaded &&
    cityStore.cities.length > 1
)

const choose = (slug: string) => {
  dismissed.value = true
  if (slug === cityStore.activeCitySlug) return
  void cityStore.setCity(slug)
}

const exploreAll = () => {
  dismissed.value = true
  void cityStore.setCity(ALL_CITIES)
}
</script>

<template>
  <div
    v-if="visible"
    class="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4"
    @click.self="dismissed = true"
  >
    <div class="bg-white rounded-2xl shadow-2xl max-w-3xl w-full p-6 md:p-8 max-h-[90vh] overflow-y-auto">
      <h2 class="font-display text-2xl md:text-3xl font-bold text-gray-900 text-center">
        {{ t('cityPicker.title') }}
      </h2>
      <p class="text-sm text-gray-600 text-center mt-2">
        {{ t('cityPicker.subtitle') }}
      </p>

      <div class="grid grid-cols-1 sm:grid-cols-2 gap-4 mt-6">
        <button
          v-for="city in cityStore.cities"
          :key="city.slug"
          type="button"
          class="relative h-40 rounded-xl overflow-hidden text-left group border border-gray-200 focus:outline-none focus:ring-2 focus:ring-primary-600"
          @click="choose(city.slug)"
        >
          <div
            class="absolute inset-0 bg-cover bg-center transition-transform duration-300 group-hover:scale-105"
            :class="{ 'bg-gradient-to-br from-primary-400 to-primary-700': !city.hero_image }"
            :style="city.hero_image ? { backgroundImage: `url('${city.hero_image}')` } : {}"
          ></div>
          <div class="absolute inset-0 bg-gradient-to-t from-black/70 via-black/20 to-transparent"></div>
          <div class="absolute bottom-0 left-0 right-0 p-4">
            <div class="text-white text-lg font-bold">{{ city.name }}</div>
            <div class="text-white/80 text-xs">
              {{ [city.region, city.country_name].filter(Boolean).join(', ') }}
            </div>
          </div>
        </button>
      </div>

      <div class="flex flex-col sm:flex-row items-center justify-center gap-3 mt-6">
        <button
          type="button"
          class="text-sm font-medium text-primary-700 hover:text-primary-900 underline"
          @click="exploreAll"
        >
          {{ t('cityPicker.exploreAll') }}
        </button>
        <span class="hidden sm:inline text-gray-300">·</span>
        <button
          type="button"
          class="text-sm text-gray-500 hover:text-gray-700 underline"
          @click="dismissed = true"
        >
          {{ t('cityPicker.keepCurrent', { city: cityStore.activeCity?.name || '' }) }}
        </button>
      </div>
    </div>
  </div>
</template>
