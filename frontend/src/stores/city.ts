import { defineStore } from 'pinia';
import { computed, ref } from 'vue';
import { cityService, setRequestCity, CITY_STORAGE_KEY, ALL_CITIES } from '@/services/api';
import type { City } from '@/types/city';

/**
 * City Store — the multi-city anchor.
 *
 * Two layers, deliberately separate:
 *
 *  - `chosenSlug` is what the user explicitly picked (header switcher, gateway
 *    card, ?city= adoption). It is persisted in localStorage and scopes the
 *    unprefixed account/management pages.
 *  - `urlSlug` is whatever city the current URL names. CityShellView sets it
 *    on entering /:citySlug and releases it on leaving. It lives in memory
 *    only, so it is per-tab.
 *
 * `activeCitySlug` is the URL's city when there is one, else the chosen one,
 * and it drives X-City through the axios interceptor. Keeping browsing out of
 * localStorage is what stops two tabs on two cities from overwriting each
 * other's scope, and stops a shared cross-city link from silently re-pointing
 * someone's account pages at a city they never chose.
 *
 * Switching city clears the service-worker API cache (its responses are keyed
 * by URL only — a header does not vary the key, so the offline fallback would
 * otherwise serve the previous city) and does a full page load: every view
 * refetches on mount, which is simpler and safer than wiring reactive
 * refetches through every store.
 */
export const useCityStore = defineStore('city', () => {
    const cities = ref<City[]>([]);
    /** The city the user explicitly chose (persisted, shared across tabs). */
    const chosenSlug = ref<string | null>(localStorage.getItem(CITY_STORAGE_KEY));
    /** The city the current URL names (in-memory, per-tab). */
    const urlSlug = ref<string | null>(null);
    const activeCitySlug = computed(() => urlSlug.value ?? chosenSlug.value);
    const loaded = ref(false);
    /** True when the last catalog fetch failed — drives retry affordances. */
    const loadError = ref(false);
    // Shared in-flight request: App.vue, CityShellView and GatewayView all
    // call load() on first paint, and `loaded` only flips after the await.
    let inflight: Promise<void> | null = null;

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

    /**
     * Fetch the city catalog once. Concurrent callers share the in-flight
     * request; `force` re-fetches (retry after a failure, or after the UI
     * locale changed — city name/description are server-translated).
     */
    async function load(force = false): Promise<void> {
        if (force) {
            loaded.value = false;
            inflight = null;
        }
        if (loaded.value) return;
        if (inflight) return inflight;
        inflight = (async () => {
            try {
                const response = await cityService.list();
                cities.value = Array.isArray(response.data) ? response.data : [];
                loaded.value = true;
                loadError.value = false;
                // Self-heal a stale/deactivated chosen slug (the all-cities
                // sentinel is always "known").
                const first = cities.value[0];
                if (first) {
                    const known =
                        chosenSlug.value === ALL_CITIES ||
                        cities.value.some((c) => c.slug === chosenSlug.value);
                    if (!known) {
                        chosenSlug.value = first.slug;
                    }
                    localStorage.setItem(CITY_STORAGE_KEY, chosenSlug.value as string);
                }
            } catch {
                // Catalog unavailable (offline/older backend): keep whatever slug
                // is persisted and let callers surface a retry.
                loadError.value = true;
            } finally {
                inflight = null;
            }
        })();
        return inflight;
    }

    async function clearApiCache() {
        if (typeof caches === 'undefined') return;
        try {
            await caches.delete('api-v1');
        } catch {
            // Best effort — never block a city switch on cache clearing.
        }
    }

    /** Current document location, including query and hash. */
    function currentLocation() {
        return window.location.pathname + window.location.search + window.location.hash;
    }

    /**
     * Header switcher: persist + full page load. `targetPath` defaults to
     * staying exactly where the user is (the old `reload()` behaviour), which
     * is the right answer for every unprefixed account/management page —
     * callers on a city URL pass the re-prefixed path instead.
     */
    async function setCity(slug: string, targetPath?: string) {
        if (!slug) return;
        const target = targetPath ?? currentLocation();
        if (slug === activeCitySlug.value && target === currentLocation()) return;
        // An explicit choice: this one *is* persisted across tabs and sessions.
        chosenSlug.value = slug;
        localStorage.setItem(CITY_STORAGE_KEY, slug);
        await clearApiCache();
        window.location.assign(target);
    }

    /**
     * Scope this tab to a URL slug the caller has already validated against
     * the catalog (CityShellView). Deliberately NOT persisted: browsing a city
     * is not choosing one. Awaits the service-worker purge — `api-v1`
     * responses are keyed by URL only, so a child that fetches before the
     * purge lands would be served the previous city's payload.
     */
    async function adoptSlug(slug: string) {
        if (!slug || slug === activeCitySlug.value) {
            urlSlug.value = slug || urlSlug.value;
            setRequestCity(activeCitySlug.value);
            return;
        }
        urlSlug.value = slug;
        setRequestCity(slug);
        await clearApiCache();
    }

    /** Leaving the city shell: unprefixed pages fall back to the chosen city. */
    function releaseUrlCity() {
        if (urlSlug.value === null) return;
        urlSlug.value = null;
        setRequestCity(null);
    }

    return {
        cities,
        activeCitySlug,
        chosenSlug,
        loaded,
        loadError,
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
        releaseUrlCity,
    };
});
