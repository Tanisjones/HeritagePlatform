<script setup lang="ts">
import { useI18n } from 'vue-i18n'

const { t } = useI18n()
</script>

<template>
  <div class="min-h-[60vh] flex items-center justify-center px-4">
    <div class="text-center max-w-md">
      <p class="font-display text-6xl font-bold text-primary-600">404</p>
      <h1 class="mt-4 text-2xl font-bold text-gray-900">{{ t('notFound.title') }}</h1>
      <p class="mt-2 text-gray-600">{{ t('notFound.message') }}</p>
      <RouterLink
        to="/"
        class="inline-block mt-6 px-5 py-2.5 rounded-lg bg-primary-600 text-white font-medium hover:bg-primary-700 transition-colors"
      >
        {{ t('notFound.backHome') }}
      </RouterLink>
    </div>
  </div>
</template>
