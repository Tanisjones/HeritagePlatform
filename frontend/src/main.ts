import { createApp } from 'vue'
import './style.css'
import App from './App.vue'
import router from './router'
import i18n from './i18n'
import { pinia } from './pinia'
// import { registerSW } from 'virtual:pwa-register'

const app = createApp(App)

app.use(pinia)
app.use(router)
app.use(i18n)
app.mount('#app')

// registerSW({
// 	immediate: true,
// })
