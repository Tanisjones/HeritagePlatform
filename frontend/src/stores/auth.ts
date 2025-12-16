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

    const isCurator = computed(() => isAuthenticated.value && roleSlug.value === 'curator');
    const isTeacher = computed(() => isAuthenticated.value && roleSlug.value === 'teacher');
    const isContributor = computed(() => isAuthenticated.value);
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

    function logout() {
        token.value = null;
        user.value = null;
        localStorage.removeItem('token');
        localStorage.removeItem('user');
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
        isCurator,
        isTeacher,
        isContributor,
        hasPermission,
        displayName,
        setAuth,
        logout,
        loadUserIfNeeded
    };
});
