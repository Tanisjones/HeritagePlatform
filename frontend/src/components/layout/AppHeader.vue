<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useCityStore } from '@/stores/city'
import { useCityPath } from '@/composables/useCityPath'
import { ALL_SEGMENT, segmentForSlug, swapCitySegment } from '@/router/cityContext'
import { ALL_CITIES } from '@/services/api'
import NotificationBell from '@/components/notifications/NotificationBell.vue'
import { useI18n } from 'vue-i18n'

const mobileMenuOpen = ref(false)
const userDropdownOpen = ref(false)
const authStore = useAuthStore()
const cityStore = useCityStore()
const route = useRoute()
const { cityPath } = useCityPath()
const { t, locale } = useI18n()

// The gateway (/) is the platform front page: no city context, so no city
// nav or switcher — only brand, language and auth. The same applies when the
// URL names a city that does not exist: the shell renders a 404 there, and
// city links built from that slug would just be more 404s.
const isGateway = computed(() => route.name === 'gateway')
const isUnknownCity = computed(() => {
  const segment = route.params.citySlug
  if (typeof segment !== 'string' || !segment) return false
  if (segment === ALL_SEGMENT) return false
  if (!cityStore.loaded || cityStore.cities.length === 0) return false
  return !cityStore.cities.some((c) => c.slug === segment)
})
/** No usable city context: suppress city nav, switcher and logo. */
const noCityContext = computed(() => isGateway.value || isUnknownCity.value)

const onCityChange = (event: Event) => {
  const slug = (event.target as HTMLSelectElement).value
  const segment = segmentForSlug(slug)
  // Where the switch lands is declared by the route (meta.cityScope), not
  // inferred from the shape of its params:
  //   generic city page → keep the subpath, query and hash
  //   entity page (:id belongs to one city) → the new city's home
  //   unprefixed account/management page → stay put (target stays undefined,
  //     and the store reloads the current location with the new scope)
  const onCityRoute = typeof route.params.citySlug === 'string' && !!route.params.citySlug
  let target: string | undefined
  if (onCityRoute) {
    const scope = route.matched.reduce<string | undefined>(
      (acc, record) => (record.meta.cityScope as string | undefined) ?? acc,
      undefined
    )
    // route.fullPath minus route.path is exactly '?query#hash'.
    const suffix = route.fullPath.slice(route.path.length)
    target =
      scope === 'entity' ? `/${segment}` : swapCitySegment(route.path, segment) + suffix
  }
  cityStore.setCity(slug, target)
}

// Single source of truth for the primary nav, rendered in both the desktop bar
// and the mobile menu — no more two hand-maintained copies that drift apart.
// Content links carry the city prefix (current route's city, else the
// persisted one); account/management links stay unprefixed.
interface NavLink {
  to: string
  labelKey: string
  visible?: () => boolean
}
// City-scoped content links: meaningless on the gateway, which has no city.
const contentNav = computed<NavLink[]>(() => [
  { to: cityPath(''), labelKey: 'nav.home' },
  { to: cityPath('/explore'), labelKey: 'nav.explore' },
  { to: cityPath('/routes'), labelKey: 'nav.routes' },
  { to: cityPath('/learn'), labelKey: 'nav.learn' },
  { to: cityPath('/contribute'), labelKey: 'nav.contribute' },
])
// Management links are unprefixed and need no city, so they stay reachable
// everywhere — including the gateway, which is where the brand logo and the
// 404 page send people.
const manageNav = computed<NavLink[]>(() => [
  { to: '/moderation', labelKey: 'nav.moderation', visible: () => !!(authStore.isCurator || authStore.user?.is_staff) },
  { to: '/teach', labelKey: 'nav.teach', visible: () => !!(authStore.isTeacher || authStore.user?.is_staff) },
])
const primaryNav = computed<NavLink[]>(() =>
  noCityContext.value ? manageNav.value : [...contentNav.value, ...manageNav.value]
)
// Authenticated "My account" links (dropdown on desktop, section on mobile).
const accountNav = computed<NavLink[]>(() => [
  { to: '/dashboard', labelKey: 'nav.dashboard' },
  { to: cityPath('/routes/my'), labelKey: 'nav.myRoutes' },
  { to: cityPath('/routes/active'), labelKey: 'nav.activeRoutes' },
  { to: '/my-contributions', labelKey: 'nav.myContributions' },
  { to: '/notifications', labelKey: 'nav.notifications' },
  {
    to: '/admin/ai-usage',
    labelKey: 'nav.aiUsage',
    visible: () => !!(authStore.isCurator || authStore.user?.is_staff),
  },
])
const visiblePrimaryNav = computed(() => primaryNav.value.filter((l) => !l.visible || l.visible()))
const visibleAccountNav = computed(() => accountNav.value.filter((l) => !l.visible || l.visible()))

const LOCALE_STORAGE_KEY = 'hp_locale'

watch(locale, (newLocale) => {
  if (typeof newLocale === 'string') {
    localStorage.setItem(LOCALE_STORAGE_KEY, newLocale)
  }
})

const logout = () => {
  authStore.logout()
  mobileMenuOpen.value = false
  userDropdownOpen.value = false
}

const toggleUserDropdown = () => {
  userDropdownOpen.value = !userDropdownOpen.value
}

const closeUserDropdown = (event: MouseEvent) => {
  const target = event.target as HTMLElement
  if (!target.closest('#user-menu-button') && !target.closest('#user-menu-dropdown')) {
    userDropdownOpen.value = false
  }
}

onMounted(() => {
  document.addEventListener('click', closeUserDropdown)
})

onUnmounted(() => {
  document.removeEventListener('click', closeUserDropdown)
})
</script>

<template>
  <header class="bg-white shadow-md relative z-50">
    <nav class="container mx-auto px-4 py-3">
      <div class="flex items-center justify-between md:grid md:grid-cols-3">
        <!-- Logo -->
        <RouterLink to="/" class="flex items-center space-x-2 md:justify-self-start">
          <!-- C3: the active city's logo, when it has one -->
          <img
            v-if="!noCityContext && cityStore.activeCity?.logo"
            :src="cityStore.activeCity.logo"
            :alt="cityStore.activeCity.name"
            class="h-8 w-8 rounded object-contain"
          />
          <span class="text-2xl font-display font-bold text-primary-600">
            {{ t('common.brand') }}
          </span>
        </RouterLink>

        <!-- Desktop Navigation (content links drop out on the gateway: no city context there) -->
        <div class="hidden md:flex items-center space-x-6 md:justify-self-center">
          <RouterLink
            v-for="link in visiblePrimaryNav"
            :key="link.to"
            :to="link.to"
            class="text-gray-700 hover:text-primary-600 transition-colors font-medium"
          >
            {{ t(link.labelKey) }}
          </RouterLink>
        </div>

        <!-- Auth Buttons / User Menu -->
        <div class="hidden md:flex items-center space-x-3 md:justify-self-end">
          <!-- City Switcher (only when the platform hosts more than one city) -->
          <div v-if="!noCityContext && cityStore.hasMultipleCities" class="flex items-center border-r border-gray-300 pr-3 mr-2">
            <select
              :value="cityStore.switcherValue"
              @change="onCityChange"
              :aria-label="t('common.citySwitcher')"
              class="bg-transparent border-none text-gray-700 font-medium focus:ring-0 cursor-pointer py-1"
            >
              <option v-for="city in cityStore.cities" :key="city.slug" :value="city.slug">
                {{ city.name }}
              </option>
              <!-- C1: explicit unscoped mode — no X-City header, badges on cards -->
              <option :value="ALL_CITIES">{{ t('common.allCities') }}</option>
            </select>
          </div>

          <!-- Language Switcher -->
          <div class="flex items-center border-r border-gray-300 pr-3 mr-2">
            <select
              v-model="locale"
              class="bg-transparent border-none text-gray-700 font-medium focus:ring-0 cursor-pointer py-1"
            >
              <option value="es">ES</option>
              <option value="en">EN</option>
            </select>
          </div>

          <template v-if="authStore.isAuthenticated">
            <NotificationBell />
            
            <!-- User Dropdown -->
            <div class="relative">
              <button
                id="user-menu-button"
                @click="toggleUserDropdown"
                class="flex items-center space-x-2 px-3 py-2 rounded-lg hover:bg-gray-100 transition-colors focus:outline-none"
              >
                <span class="text-gray-700 font-medium">{{ authStore.displayName }}</span>
                <svg class="w-4 h-4 text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
                </svg>
              </button>

              <div
                v-if="userDropdownOpen"
                id="user-menu-dropdown"
                class="absolute right-0 mt-2 w-56 bg-white rounded-lg shadow-lg py-1 border border-gray-100 z-50 transform origin-top-right transition-all duration-200"
              >
                <!-- Dashboard -->
                 <RouterLink
                  to="/dashboard"
                  class="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 hover:text-primary-600"
                  @click="userDropdownOpen = false"
                >
                  {{ t('nav.dashboard') }}
                </RouterLink>

                 <RouterLink
                  to="/profile"
                  class="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 hover:text-primary-600"
                  @click="userDropdownOpen = false"
                >
                  {{ t('nav.profile') }}
                </RouterLink>

                 <RouterLink
                  to="/progress"
                  class="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 hover:text-primary-600"
                  @click="userDropdownOpen = false"
                >
                  {{ t('nav.progress') }}
                </RouterLink>
                
                <div class="border-t border-gray-100 my-1"></div>

                <!-- My Items -->
                <RouterLink
                  :to="cityPath('/routes/my')"
                  class="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 hover:text-primary-600"
                  @click="userDropdownOpen = false"
                >
                  {{ t('nav.myRoutes') }}
                </RouterLink>
                <RouterLink
                  :to="cityPath('/routes/active')"
                  class="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 hover:text-primary-600"
                  @click="userDropdownOpen = false"
                >
                  {{ t('nav.activeRoutes') }}
                </RouterLink>
                 <RouterLink
                  to="/my-contributions"
                  class="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 hover:text-primary-600"
                  @click="userDropdownOpen = false"
                >
                  {{ t('nav.myContributions') }}
                </RouterLink>

                <!-- AI-economy dashboard (staff/curator only) -->
                <template v-if="authStore.isCurator || authStore.user?.is_staff">
                  <div class="border-t border-gray-100 my-1"></div>
                  <RouterLink
                    to="/admin/ai-usage"
                    class="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 hover:text-primary-600"
                    @click="userDropdownOpen = false"
                  >
                    {{ t('nav.aiUsage') }}
                  </RouterLink>
                </template>

                <div class="border-t border-gray-100 my-1"></div>

                <!-- Logout -->
                <button
                  @click="logout"
                  class="block w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-red-50 hover:text-red-600"
                >
                  {{ t('nav.logout') }}
                </button>
              </div>
            </div>
          </template>
          <template v-else>
            <RouterLink
              to="/login"
              class="px-4 py-2 text-gray-700 hover:text-primary-600 transition-colors font-medium"
            >
              {{ t('nav.login') }}
            </RouterLink>
            <RouterLink
              to="/register"
              class="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors font-medium"
            >
              {{ t('nav.signup') }}
            </RouterLink>
          </template>
        </div>

        <!-- Mobile Menu Button -->
        <button
          class="md:hidden p-2 rounded-lg hover:bg-gray-100"
          @click="mobileMenuOpen = !mobileMenuOpen"
        >
          <svg
            class="w-6 h-6 text-gray-700"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              v-if="!mobileMenuOpen"
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M4 6h16M4 12h16M4 18h16"
            />
            <path
              v-else
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="2"
              d="M6 18L18 6M6 6l12 12"
            />
          </svg>
        </button>
      </div>

      <!-- Mobile Menu -->
      <div v-if="mobileMenuOpen" class="md:hidden mt-4 pb-4 space-y-3">
        <div
          v-if="!noCityContext && cityStore.hasMultipleCities"
          class="px-2 pb-2 mb-2 border-b border-gray-100 flex items-center space-x-3"
        >
          <span class="text-gray-500 font-medium text-sm">{{ t('common.citySwitcher') }}:</span>
          <select
            :value="cityStore.switcherValue"
            @change="onCityChange"
            class="bg-transparent border border-gray-200 rounded text-gray-700 font-medium text-sm py-1"
          >
            <option v-for="city in cityStore.cities" :key="city.slug" :value="city.slug">
              {{ city.name }}
            </option>
            <option :value="ALL_CITIES">{{ t('common.allCities') }}</option>
          </select>
        </div>
        <div class="px-2 pb-2 mb-2 border-b border-gray-100 flex items-center space-x-4">
          <span class="text-gray-500 font-medium text-sm">{{ t('learn.filters.language') }}:</span>
            <button 
                @click="locale = 'es'" 
                :class="locale === 'es' ? 'text-primary-600 font-bold' : 'text-gray-600'"
            >ES</button>
            <button 
                @click="locale = 'en'"
                :class="locale === 'en' ? 'text-primary-600 font-bold' : 'text-gray-600'"
            >EN</button>
        </div>
        <RouterLink
          v-for="link in visiblePrimaryNav"
          :key="link.to"
          :to="link.to"
          class="block py-2 text-gray-700 hover:text-primary-600 transition-colors font-medium"
          @click="mobileMenuOpen = false"
        >
          {{ t(link.labelKey) }}
        </RouterLink>

        <div class="pt-3 border-t border-gray-200 space-y-2" v-if="authStore.isAuthenticated">
             <div class="px-2 text-xs font-semibold text-gray-400 uppercase tracking-wider">
                 {{ t('nav.myAccount') }}
             </div>
             <RouterLink
              v-for="link in visibleAccountNav"
              :key="link.to"
              :to="link.to"
              class="block py-2 text-gray-700 hover:text-primary-600 transition-colors font-medium pl-2"
              @click="mobileMenuOpen = false"
            >
              {{ t(link.labelKey) }}
            </RouterLink>
            <button
              @click="logout"
              class="block w-full text-left py-2 text-gray-700 hover:text-red-600 transition-colors font-medium pl-2"
            >
              {{ t('nav.logout') }}
            </button>
        </div>
        <div class="pt-3 border-t border-gray-200 space-y-2" v-else>
            <RouterLink
              to="/login"
              class="block py-2 text-gray-700 hover:text-primary-600 transition-colors font-medium"
              @click="mobileMenuOpen = false"
            >
              {{ t('nav.login') }}
            </RouterLink>
            <RouterLink
              to="/register"
              class="block py-2 px-4 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors font-medium text-center"
              @click="mobileMenuOpen = false"
            >
              {{ t('nav.signup') }}
            </RouterLink>
        </div>
      </div>
    </nav>
  </header>
</template>
