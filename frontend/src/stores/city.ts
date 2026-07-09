import { defineStore } from 'pinia';
import { computed, ref } from 'vue';
import { cityService, CITY_STORAGE_KEY, ALL_CITIES } from '@/services/api';
import type { City } from '@/types/city';

/**
 * City Store — the multi-city anchor.
 *
 * Holds the active-city catalog and the persisted active-city slug. The axios
 * request interceptor reads the same localStorage key and sends it as X-City
 * on every API call, so all list endpoints and writes are scoped to it.
 *
 * Switching city persists the slug, clears the service-worker API cache (its
 * responses are keyed by URL only — a header does not vary the key, so the
 * offline fallback would otherwise serve the previous city) and reloads the
 * app: every view refetches on mount, which is simpler and safer than wiring
 * reactive refetches through every store.
 */
export const useCityStore = defineStore('city', () => {
    const cities = ref<City[]>([]);
    const activeCitySlug = ref<string | null>(localStorage.getItem(CITY_STORAGE_KEY));
    const loaded = ref(false);
    // C2 — true only when NOTHING was persisted before this session started
    // (load() below persists a default, so this must be captured at init).
    // Drives the one-time first-visit city picker.
    const firstVisit = ref(localStorage.getItem(CITY_STORAGE_KEY) === null);

    // C1 — explicit "Todas las ciudades" mode: no X-City header is sent (see
    // the axios interceptor) and content cards show city badges.
    const isAllCities = computed(() => activeCitySlug.value === ALL_CITIES);

    const activeCity = computed<City | null>(() => {
        if (isAllCities.value) return null;
        if (!cities.value.length) return null;
        return cities.value.find((c) => c.slug === activeCitySlug.value) ?? cities.value[0] ?? null;
    });

    /** What the header switcher should display (a city slug or the sentinel). */
    const switcherValue = computed(() =>
        isAllCities.value ? ALL_CITIES : activeCity.value?.slug
    );

    const hasMultipleCities = computed(() => cities.value.length > 1);

    /** Leaflet-ordered [lat, lng] center of the active city, if loaded. */
    const mapCenter = computed<[number, number] | null>(() => {
        const center = activeCity.value?.center;
        if (!center || !Array.isArray(center.coordinates)) return null;
        const [lng, lat] = center.coordinates;
        return [lat, lng];
    });

    const mapZoom = computed(() => activeCity.value?.default_zoom ?? 13);

    const heroImageUrl = computed(() => activeCity.value?.hero_image || null);

    async function load() {
        if (loaded.value) return;
        try {
            const response = await cityService.list();
            cities.value = Array.isArray(response.data) ? response.data : [];
            loaded.value = true;
            // Self-heal a stale/deactivated persisted slug (the all-cities
            // sentinel is always "known").
            const first = cities.value[0];
            if (first) {
                const known =
                    activeCitySlug.value === ALL_CITIES ||
                    cities.value.some((c) => c.slug === activeCitySlug.value);
                if (!known) {
                    activeCitySlug.value = first.slug;
                }
                localStorage.setItem(CITY_STORAGE_KEY, activeCitySlug.value as string);
            }
        } catch {
            // Catalog unavailable (offline/older backend): keep whatever slug is
            // persisted; the app keeps working unscoped.
        }
    }

    async function clearApiCache() {
        if (typeof caches === 'undefined') return;
        try {
            await caches.delete('api-v1');
        } catch {
            // Best effort — never block a city switch on cache clearing.
        }
    }

    async function setCity(slug: string) {
        if (!slug || slug === activeCitySlug.value) return;
        activeCitySlug.value = slug;
        localStorage.setItem(CITY_STORAGE_KEY, slug);
        await clearApiCache();
        window.location.reload();
    }

    /** ?city= deep-link: persist without reloading (router strips the param
     * before the views mount, so the first fetches already carry the slug). */
    function adoptSlug(slug: string) {
        if (!slug || slug === activeCitySlug.value) return;
        activeCitySlug.value = slug;
        localStorage.setItem(CITY_STORAGE_KEY, slug);
        void clearApiCache();
    }

    return {
        cities,
        activeCitySlug,
        loaded,
        firstVisit,
        isAllCities,
        activeCity,
        switcherValue,
        hasMultipleCities,
        mapCenter,
        mapZoom,
        heroImageUrl,
        load,
        setCity,
        adoptSlug,
    };
});
