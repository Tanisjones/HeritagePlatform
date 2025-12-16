import { createI18n } from 'vue-i18n'
import en from './locales/en.json'
import es from './locales/es.json'

const LOCALE_STORAGE_KEY = 'hp_locale'
const SUPPORTED_LOCALES = ['es', 'en'] as const
type SupportedLocale = (typeof SUPPORTED_LOCALES)[number]

const normalizeLocale = (rawLocale: string | null | undefined): SupportedLocale | null => {
    if (!rawLocale) return null

    const normalized = rawLocale.trim().toLowerCase().split('-')[0] ?? ''
    return (SUPPORTED_LOCALES as readonly string[]).includes(normalized) ? (normalized as SupportedLocale) : null
}

const getInitialLocale = (): SupportedLocale => {
    const stored = normalizeLocale(localStorage.getItem(LOCALE_STORAGE_KEY))
    if (stored) return stored

    const browserLocale = normalizeLocale(
        typeof navigator !== 'undefined'
            ? (navigator.languages && navigator.languages.length > 0 ? navigator.languages[0] : navigator.language)
            : null
    )
    if (browserLocale) return browserLocale

    return 'es'
}

const i18n = createI18n({
    locale: getInitialLocale(), // set locale
    fallbackLocale: 'en', // set fallback locale
    legacy: false, // use Composition API
    messages: {
        en,
        es
    }
})

// Persist the active locale whenever it changes.
if (i18n.global && 'locale' in i18n.global) {
    // vue-i18n v9 uses a Ref for locale when legacy: false
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const localeRef = (i18n.global as any).locale
    if (localeRef && typeof localeRef === 'object' && 'value' in localeRef) {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const current = normalizeLocale((localeRef as any).value)
        if (current) localStorage.setItem(LOCALE_STORAGE_KEY, current)
    }
}

export default i18n
