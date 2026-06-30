import { createApp } from 'vue'
import './style.css'
import App from './App.vue'
import router from './router'
import i18n from './i18n'
import { pinia } from './pinia'
import { registerSW } from 'virtual:pwa-register'

const app = createApp(App)

app.use(pinia)
app.use(router)
app.use(i18n)
app.mount('#app')

// Register the service worker (offline app shell, cached API/media/tiles, and
// the background-sync queue that retries contribution POSTs made while offline).
// autoUpdate is configured in vite.config.ts, so new versions activate on the
// next navigation without a manual prompt.
registerSW({ immediate: true })
