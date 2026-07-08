<script setup lang="ts">
import { onMounted } from 'vue'
import { RouterView } from 'vue-router'
import AppHeader from './components/layout/AppHeader.vue'
import AppDialogHost from './components/common/AppDialogHost.vue'
import { useAuthStore } from '@/stores/auth'
import { useCityStore } from '@/stores/city'

const authStore = useAuthStore()
const cityStore = useCityStore()

onMounted(() => {
  authStore.loadUserIfNeeded()
  cityStore.load()
})
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
