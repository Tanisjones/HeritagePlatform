<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { authService } from '../services/api'
import AppButton from '../components/common/AppButton.vue'
import AppCard from '../components/common/AppCard.vue'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()
const router = useRouter()
const name = ref('')
const email = ref('')
const password = ref('')
const confirmPassword = ref('')
const loading = ref(false)
const error = ref('')

const handleRegister = async () => {
  if (!name.value || !email.value || !password.value || !confirmPassword.value) {
    error.value = t('auth.errors.fillAllFields')
    return
  }

  if (password.value !== confirmPassword.value) {
    error.value = t('auth.errors.passwordsDoNotMatch')
    return
  }

  try {
    loading.value = true
    error.value = ''
    
    await authService.register({
      display_name: name.value,
      email: email.value,
      password: password.value,
      password_confirm: confirmPassword.value,
      username: email.value
    })

    // Auto login or redirect to login
    router.push('/login?registered=true')
  } catch (err: any) {
    console.error('Registration error:', err)
    if (err.response?.data) {
      const data = err.response.data;
      // Handle standard DRF error format {"field": ["Error message"]}
      const firstError = Object.values(data)[0];
      if (Array.isArray(firstError)) {
        error.value = firstError[0] as string;
      } else if (typeof firstError === 'string') {
        error.value = firstError;
      } else if (data.message) {
        error.value = data.message;
      } else {
        error.value = 'Failed to register. Please check your inputs.';
      }
    } else {
      error.value = 'Failed to register. Please try again.';
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
        {{ t('auth.register.title') }}
      </h2>
      <p class="mt-2 text-center text-sm text-gray-600">
        {{ t('auth.register.alreadyHaveAccount') }}
        <router-link to="/login" class="font-medium text-primary-600 hover:text-primary-500">
          {{ t('auth.register.signIn') }}
        </router-link>
      </p>
    </div>

    <div class="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
      <AppCard>
        <form class="space-y-6" @submit.prevent="handleRegister">
          <div>
            <label for="name" class="block text-sm font-medium text-gray-700">{{ t('auth.register.nameLabel') }}</label>
            <div class="mt-1">
              <input
                id="name"
                name="name"
                type="text"
                autocomplete="name"
                required
                v-model="name"
                class="appearance-none block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-primary-500 focus:border-primary-500 sm:text-sm"
              />
            </div>
          </div>

          <div>
            <label for="email" class="block text-sm font-medium text-gray-700">{{ t('auth.register.emailLabel') }}</label>
            <div class="mt-1">
              <input
                id="email"
                name="email"
                type="email"
                autocomplete="email"
                required
                v-model="email"
                class="appearance-none block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-primary-500 focus:border-primary-500 sm:text-sm"
              />
            </div>
          </div>

          <div>
            <label for="password" class="block text-sm font-medium text-gray-700">{{ t('auth.register.passwordLabel') }}</label>
            <div class="mt-1">
              <input
                id="password"
                name="password"
                type="password"
                autocomplete="new-password"
                required
                v-model="password"
                class="appearance-none block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-primary-500 focus:border-primary-500 sm:text-sm"
              />
            </div>
          </div>

          <div>
            <label for="confirmPassword" class="block text-sm font-medium text-gray-700">{{ t('auth.register.confirmPasswordLabel') }}</label>
            <div class="mt-1">
              <input
                id="confirmPassword"
                name="confirmPassword"
                type="password"
                autocomplete="new-password"
                required
                v-model="confirmPassword"
                class="appearance-none block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm placeholder-gray-400 focus:outline-none focus:ring-primary-500 focus:border-primary-500 sm:text-sm"
              />
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
              {{ loading ? t('auth.register.loading') : t('auth.register.submit') }}
            </AppButton>
          </div>
        </form>
      </AppCard>
    </div>
  </div>
</template>
