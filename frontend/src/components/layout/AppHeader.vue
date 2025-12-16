<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue'
import { RouterLink } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import NotificationBell from '@/components/notifications/NotificationBell.vue'
import { useI18n } from 'vue-i18n'

const mobileMenuOpen = ref(false)
const userDropdownOpen = ref(false)
const authStore = useAuthStore()
const { t, locale } = useI18n()

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
          <span class="text-2xl font-display font-bold text-primary-600">
            {{ t('common.brand') }}
          </span>
        </RouterLink>

        <!-- Desktop Navigation -->
        <div class="hidden md:flex items-center space-x-6 md:justify-self-center">
          <RouterLink
            to="/"
            class="text-gray-700 hover:text-primary-600 transition-colors font-medium"
          >
            {{ t('nav.home') }}
          </RouterLink>
          <RouterLink
            to="/explore"
            class="text-gray-700 hover:text-primary-600 transition-colors font-medium"
          >
            {{ t('nav.explore') }}
          </RouterLink>
          <RouterLink
            to="/routes"
            class="text-gray-700 hover:text-primary-600 transition-colors font-medium"
          >
            {{ t('nav.routes') }}
          </RouterLink>
          <RouterLink
            to="/learn"
            class="text-gray-700 hover:text-primary-600 transition-colors font-medium"
          >
            {{ t('nav.learn') }}
          </RouterLink>
          <RouterLink
            to="/contribute"
            class="text-gray-700 hover:text-primary-600 transition-colors font-medium"
          >
            {{ t('nav.contribute') }}
          </RouterLink>
          <RouterLink
            v-if="authStore.isCurator || authStore.user?.is_staff"
            to="/moderation"
            class="text-gray-700 hover:text-primary-600 transition-colors font-medium"
          >
            {{ t('nav.moderation') }}
          </RouterLink>
        </div>

        <!-- Auth Buttons / User Menu -->
        <div class="hidden md:flex items-center space-x-3 md:justify-self-end">
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
                  to="/routes/my"
                  class="block px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 hover:text-primary-600"
                  @click="userDropdownOpen = false"
                >
                  {{ t('nav.myRoutes') }}
                </RouterLink>
                <RouterLink
                  to="/routes/active"
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
          to="/"
          class="block py-2 text-gray-700 hover:text-primary-600 transition-colors font-medium"
          @click="mobileMenuOpen = false"
        >
          {{ t('nav.home') }}
        </RouterLink>
        <RouterLink
          to="/explore"
          class="block py-2 text-gray-700 hover:text-primary-600 transition-colors font-medium"
          @click="mobileMenuOpen = false"
        >
          {{ t('nav.explore') }}
        </RouterLink>
        <RouterLink
          to="/routes"
          class="block py-2 text-gray-700 hover:text-primary-600 transition-colors font-medium"
          @click="mobileMenuOpen = false"
        >
          {{ t('nav.routes') }}
        </RouterLink>
        <RouterLink
          to="/learn"
          class="block py-2 text-gray-700 hover:text-primary-600 transition-colors font-medium"
          @click="mobileMenuOpen = false"
        >
          {{ t('nav.learn') }}
        </RouterLink>
        <RouterLink
          to="/contribute"
          class="block py-2 text-gray-700 hover:text-primary-600 transition-colors font-medium"
          @click="mobileMenuOpen = false"
        >
          {{ t('nav.contribute') }}
        </RouterLink>
        <RouterLink
          v-if="authStore.isCurator || authStore.user?.is_staff"
          to="/moderation"
          class="block py-2 text-gray-700 hover:text-primary-600 transition-colors font-medium"
          @click="mobileMenuOpen = false"
        >
          {{ t('nav.moderation') }}
        </RouterLink>
        
        <div class="pt-3 border-t border-gray-200 space-y-2" v-if="authStore.isAuthenticated">
             <div class="px-2 text-xs font-semibold text-gray-400 uppercase tracking-wider">
                 My Account
             </div>
             <RouterLink
              to="/dashboard"
              class="block py-2 text-gray-700 hover:text-primary-600 transition-colors font-medium pl-2"
              @click="mobileMenuOpen = false"
            >
              Dashboard
            </RouterLink>
            <RouterLink
              to="/routes/my"
              class="block py-2 text-gray-700 hover:text-primary-600 transition-colors font-medium pl-2"
              @click="mobileMenuOpen = false"
            >
              {{ t('nav.myRoutes') }}
            </RouterLink>
            <RouterLink
              to="/routes/active"
              class="block py-2 text-gray-700 hover:text-primary-600 transition-colors font-medium pl-2"
              @click="mobileMenuOpen = false"
            >
              {{ t('nav.activeRoutes') }}
            </RouterLink>
             <RouterLink
              to="/my-contributions"
              class="block py-2 text-gray-700 hover:text-primary-600 transition-colors font-medium pl-2"
              @click="mobileMenuOpen = false"
            >
              {{ t('nav.myContributions') }}
            </RouterLink>
            <RouterLink
              to="/notifications"
              class="block py-2 text-gray-700 hover:text-primary-600 transition-colors font-medium pl-2"
              @click="mobileMenuOpen = false"
            >
              {{ t('nav.notifications') }}
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
