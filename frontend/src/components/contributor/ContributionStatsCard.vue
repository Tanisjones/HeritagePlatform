<script setup lang="ts">
import { useI18n } from 'vue-i18n'

defineProps<{
  total: number
  pending: number
  changesRequested: number
  published: number
  rejected: number
}>()

const { t } = useI18n()
</script>

<template>
  <section class="bg-white border border-gray-200 rounded-xl p-5">
    <h2 class="text-lg font-semibold text-gray-900 mb-4">{{ t('myContributions.stats.title') }}</h2>
    <div class="grid grid-cols-2 md:grid-cols-5 gap-3">
      <div class="rounded-lg border border-gray-200 p-3">
        <div class="text-xs text-gray-600">{{ t('myContributions.stats.total') }}</div>
        <div class="text-2xl font-bold text-gray-900">{{ total }}</div>
      </div>
      <div class="rounded-lg border border-amber-100 bg-amber-50 p-3">
        <div class="text-xs text-amber-800">{{ t('myContributions.stats.pending') }}</div>
        <div class="text-2xl font-bold text-amber-900">{{ pending }}</div>
      </div>
      <div class="rounded-lg border border-primary-100 bg-primary-50 p-3">
        <div class="text-xs text-primary-800">{{ t('myContributions.stats.changes') }}</div>
        <div class="text-2xl font-bold text-primary-900">{{ changesRequested }}</div>
      </div>
      <div class="rounded-lg border border-green-100 bg-green-50 p-3">
        <div class="text-xs text-green-800">{{ t('myContributions.stats.published') }}</div>
        <div class="text-2xl font-bold text-green-900">{{ published }}</div>
      </div>
      <div class="rounded-lg border border-red-100 bg-red-50 p-3">
        <div class="text-xs text-red-800">{{ t('myContributions.stats.rejected') }}</div>
        <div class="text-2xl font-bold text-red-900">{{ rejected }}</div>
      </div>
    </div>
  </section>
</template>

