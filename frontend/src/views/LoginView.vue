<script setup lang="ts">
import { ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { authService } from '../services/api'
import { useAuthStore } from '@/stores/auth'
import AppButton from '../components/common/AppButton.vue'
import AppCard from '../components/common/AppCard.vue'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()
const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()
const email = ref('')
const password = ref('')
const loading = ref(false)
const error = ref('')
const successMessage = ref('')

if (route.query.registered) {
  successMessage.value = t('auth.login.success')
}

const handleLogin = async () => {
  if (!email.value || !password.value) {
    error.value = t('auth.errors.fillAllFields')
    return
  }

  try {
    loading.value = true
    error.value = ''
    
    const response = await authService.login({
      email: email.value,
      password: password.value
    })

    const token = response.data.tokens.access
    const user = response.data.user
    authStore.setAuth(token, user)
    
    const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : '/'
    router.push(redirect)
  } catch (err: any) {
    console.error('Login error:', err)
    if (err.response?.data) {
      const data = err.response.data;
      // Handle standard DRF error format {"non_field_errors": ["Error message"]}
      const firstError = Object.values(data)[0];
      if (Array.isArray(firstError)) {
        error.value = firstError[0] as string;
      } else if (typeof firstError === 'string') {
        error.value = firstError;
      } else if (data.detail) {
        error.value = data.detail;
      } else {
        error.value = 'Failed to login. Please check your credentials.';
      }
    } else {
       error.value = 'Failed to login. Please try again.';
    }
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="min-h-screen bg-gray-50 flex flex-col justify-center py-12 sm:px-6 lg:px-8">
    <div class="sm:mx-auto sm:w-full sm:max-w-md">
      <h2 class="mt-6 text-center text-3xl font-display font-bold text-gray-900">
        {{ t('auth.login.welcome') }}
      </h2>
      <p class="mt-2 text-center text-sm text-gray-600">
        {{ t('auth.login.or') }}
        <router-link to="/register" class="font-medium text-primary-600 hover:text-primary-500">
          {{ t('auth.login.createAccount') }}
        </router-link>
      </p>
    </div>

    <div class="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
      <AppCard>
        <form class="space-y-6" @submit.prevent="handleLogin">
          <div>
            <label for="email" class="block text-sm font-medium text-gray-700">{{ t('auth.login.emailLabel') }}</label>
            <div class="mt-1">
              <input
                id="email"
                name="email"
                type="text"
                autocomplete="email"
                required
                v-model="email"
                class="appearance-none block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-primary-500 focus:border-primary-500 sm:text-sm"
              />
            </div>
          </div>

          <div>
            <label for="password" class="block text-sm font-medium text-gray-700">{{ t('auth.login.passwordLabel') }}</label>
            <div class="mt-1">
              <input
                id="password"
                name="password"
                type="password"
                autocomplete="current-password"
                required
                v-model="password"
                class="appearance-none block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-primary-500 focus:border-primary-500 sm:text-sm"
              />
            </div>
          </div>

          <div v-if="successMessage" class="rounded-md bg-green-50 p-4 mb-4">
            <div class="flex">
              <div class="flex-shrink-0">
                <svg class="h-5 w-5 text-green-400" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                  <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />
                </svg>
              </div>
              <div class="ml-3">
                <h3 class="text-sm font-medium text-green-800">
                  {{ successMessage }}
                </h3>
              </div>
            </div>
          </div>

          <div v-if="error" class="text-red-600 text-sm text-center">
            {{ error }}
          </div>

          <div>
            <AppButton
              type="submit"
              class="w-full flex justify-center py-2 px-4 shadow-sm text-sm font-medium"
              :disabled="loading"
            >
              {{ loading ? t('auth.login.loading') : t('auth.login.submit') }}
            </AppButton>
          </div>
        </form>
      </AppCard>
    </div>
  </div>
</template>
