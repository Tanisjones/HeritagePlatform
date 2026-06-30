import { config } from '@vue/test-utils'
import { createI18n } from 'vue-i18n'
import en from '@/i18n/locales/en.json'
import es from '@/i18n/locales/es.json'

// Register a real i18n instance globally so any component that calls
// `useI18n()` renders correctly under test. A fresh instance (rather than the
// app singleton) keeps tests isolated and free of localStorage side effects.
const i18n = createI18n({
  legacy: false,
  locale: 'es',
  fallbackLocale: 'en',
  messages: { en, es },
})

config.global.plugins = [...(config.global.plugins ?? []), i18n]

// RouterLink is stubbed by default so view/component specs don't need a router.
config.global.stubs = {
  ...(config.global.stubs as Record<string, unknown> ?? {}),
  RouterLink: { template: '<a><slot /></a>' },
}
