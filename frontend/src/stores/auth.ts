import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import { authService } from '@/services/api';

/**
 * Auth Store
 * Manages user authentication state, tokens, and role-based permissions.
 * Persists state to localStorage to survive page reloads.
 */
export const useAuthStore = defineStore('auth', () => {
    const token = ref<string | null>(localStorage.getItem('token'));
    const user = ref<any | null>(JSON.parse(localStorage.getItem('user') || 'null'));

    const isAuthenticated = computed(() => !!token.value);
    const roleSlug = computed(() => user.value?.profile?.role?.slug as string | undefined);
    const rolePermissions = computed<Record<string, any>>(() => user.value?.profile?.role?.permissions || {});

    /** Per-city governance grants from /users/me (multi-city). */
    const cityRoles = computed<Array<{ city: { id: number; slug: string; name: string }; role: string }>>(
        () => user.value?.city_roles ?? []
    );

    // Curator = a CityRole grant in ANY city (or staff). Gates the curator nav;
    // the server enforces the per-city scope on every request. The legacy
    // profile.role 'curator' slug is kept as a fallback for stale cached users
    // (it degrades safely: the API rejects what the grant doesn't cover).
    const isCurator = computed(() =>
        isAuthenticated.value && (
            !!user.value?.is_staff ||
            cityRoles.value.some((assignment) => assignment.role === 'curator') ||
            roleSlug.value === 'curator'
        )
    );
    const isTeacher = computed(() => isAuthenticated.value && roleSlug.value === 'teacher');
    const isContributor = computed(() => isAuthenticated.value);

    function isCuratorOf(citySlug: string | null | undefined): boolean {
        if (!isAuthenticated.value) return false;
        if (user.value?.is_staff) return true;
        if (!citySlug) return false;
        return cityRoles.value.some(
            (assignment) => assignment.role === 'curator' && assignment.city?.slug === citySlug
        );
    }
    const displayName = computed(() => {
        const profileName = user.value?.profile?.display_name;
        if (typeof profileName === 'string' && profileName.trim()) return profileName.trim();

        const username = user.value?.username;
        if (typeof username === 'string' && username.trim()) return username.trim();

        const email = user.value?.email;
        if (typeof email === 'string' && email.trim()) return email.trim();

        return 'Account';
    });

    function hasPermission(permission: string): boolean {
        if (!isAuthenticated.value) return false;
        if (user.value?.is_staff) return true;
        return !!rolePermissions.value?.[permission];
    }

    function setAuth(newToken: string, newUser: any) {
        token.value = newToken;
        user.value = newUser;
        localStorage.setItem('token', newToken);
        localStorage.setItem('user', JSON.stringify(newUser));
    }

    // Drop all service-worker caches. SW responses are keyed by URL only (the
    // JWT is not part of the key), so without this a previous user's cached
    // API data could be served to the next user on a shared device.
    async function clearServiceWorkerCaches() {
        if (typeof caches === 'undefined') return;
        try {
            const keys = await caches.keys();
            await Promise.all(keys.map((key) => caches.delete(key)));
        } catch {
            // Best effort — never block logout on cache clearing.
        }
    }

    function logout() {
        token.value = null;
        user.value = null;
        localStorage.removeItem('token');
        localStorage.removeItem('user');
        void clearServiceWorkerCaches();
    }

    async function loadUserIfNeeded() {
        if (!token.value || user.value) return;
        try {
            const response = await authService.me();
            user.value = response.data;
            localStorage.setItem('user', JSON.stringify(response.data));
        } catch {
            logout();
        }
    }

    return {
        token,
        user,
        isAuthenticated,
        cityRoles,
        isCurator,
        isCuratorOf,
        isTeacher,
        isContributor,
        hasPermission,
        displayName,
        setAuth,
        logout,
        loadUserIfNeeded
    };
});
