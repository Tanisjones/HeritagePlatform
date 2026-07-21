<script setup lang="ts">
import { computed, onMounted, watch } from 'vue'
import { RouterView, useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import AppHeader from './components/layout/AppHeader.vue'
import AppDialogHost from './components/common/AppDialogHost.vue'
import { useAuthStore } from '@/stores/auth'
import { useCityStore } from '@/stores/city'
import { ALL_SEGMENT } from '@/router/cityContext'
import { applyCityTheme } from '@/utils/cityTheme'

const authStore = useAuthStore()
const cityStore = useCityStore()
const route = useRoute()
const { locale } = useI18n()

onMounted(() => {
  authStore.loadUserIfNeeded()
  cityStore.load()
})

// City name/description are translated server-side (django-modeltranslation,
// selected by Accept-Language), so the cached catalog goes stale when the user
// flips the language — refetch instead of leaving a half-translated page.
watch(locale, () => {
  void cityStore.load(true)
})

// C3 — re-theme the primary palette around a city's brand color. The URL
// decides which city: platform default on the gateway, the route's city on
// /:citySlug pages ('all' → default), and the persisted active city on the
// unprefixed account pages.
const themeCity = computed(() => {
  if (route.name === 'gateway') return null
  const slug = route.params.citySlug
  if (typeof slug === 'string' && slug) {
    if (slug === ALL_SEGMENT) return null
    return cityStore.cities.find((c) => c.slug === slug) ?? null
  }
  return cityStore.activeCity
})

watch(themeCity, (city) => applyCityTheme(city), { immediate: true })
</script>

<template>
  <div class="flex flex-col min-h-screen">
    <AppHeader />
    <main class="flex-grow">
      <RouterView />
    </main>
    <AppDialogHost />
  </div>
</template>

<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Playfair+Display:wght@700&display=swap');

#app {
  font-family: 'Inter', system-ui, -apple-system, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

.font-display {
  font-family: 'Playfair Display', serif;
}
</style>
