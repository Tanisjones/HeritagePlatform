<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useModerationStore } from '@/stores/moderation'
import { useAuthStore } from '@/stores/auth'
import { useCityStore } from '@/stores/city'
import { ALL_CITIES } from '@/services/api'
import { useI18n } from 'vue-i18n'

const router = useRouter()
const moderationStore = useModerationStore()
const authStore = useAuthStore()
const cityStore = useCityStore()
const { t } = useI18n()

// D1 — the cities this curator can act in (staff: the whole catalog). Drives
// the "Estás moderando" selector; switching goes through the normal city
// switch (persist + reload) so the queue, stats and every list re-scope.
const curatorCities = computed(() => {
  if (authStore.user?.is_staff) return cityStore.cities.map((c) => ({ slug: c.slug, name: c.name }))
  return (authStore.user?.city_roles ?? [])
    .filter((r: any) => r.role === 'curator')
    .map((r: any) => ({ slug: r.city.slug, name: r.city.name }))
})

const moderatingLabel = computed(() =>
  cityStore.isAllCities ? t('common.allCities') : cityStore.activeCity?.name ?? '—'
)

const onModerationCityChange = (event: Event) => {
  cityStore.setCity((event.target as HTMLSelectElement).value)
}

// The per-city workload table is only interesting for multi-city curators.
const cityBreakdown = computed(() => moderationStore.stats?.cities ?? [])

onMounted(async () => {
  await moderationStore.fetchStats()
})
</script>

<template>
  <div class="container mx-auto px-4 py-8">
    <div class="flex items-center justify-between mb-2">
      <h1 class="text-3xl font-bold text-gray-900">{{ t('curator.title') }}</h1>
      <div class="flex gap-3">
        <button
          class="px-4 py-2 rounded-lg border border-primary-600 text-primary-600 hover:bg-primary-50 bg-white"
          @click="router.push('/moderation/resources')"
        >
          {{ t('curator.manageResources', 'Manage Resources') }}
        </button>
        <button
          class="px-4 py-2 rounded-lg border border-primary-600 text-primary-600 hover:bg-primary-50 bg-white"
          @click="router.push('/moderation/ai-suggestions')"
        >
          {{ t('curator.aiSuggestions', 'AI Suggestions') }}
        </button>
        <button
          class="px-4 py-2 rounded-lg bg-primary-600 text-white hover:bg-primary-700"
          @click="router.push('/moderation/queue')"
        >
          {{ t('curator.openQueue') }}
        </button>
      </div>
    </div>

    <!-- D1: which city this dashboard (and the queue) is scoped to -->
    <div class="flex flex-wrap items-center gap-2 mb-6 text-sm">
      <span class="text-gray-600">{{ t('curator.moderating') }}</span>
      <span class="font-semibold text-primary-800 bg-primary-50 border border-primary-100 rounded-full px-3 py-1">
        {{ moderatingLabel }}
      </span>
      <select
        v-if="curatorCities.length > 1"
        :value="cityStore.isAllCities ? ALL_CITIES : cityStore.activeCity?.slug"
        class="rounded-lg border-gray-300 text-sm py-1"
        @change="onModerationCityChange"
      >
        <option v-for="c in curatorCities" :key="c.slug" :value="c.slug">{{ c.name }}</option>
        <option :value="ALL_CITIES">{{ t('common.allCities') }}</option>
      </select>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
      <div class="bg-white border border-gray-200 rounded-xl p-5">
        <div class="text-sm text-gray-600">{{ t('curator.stats.pending') }}</div>
        <div class="text-3xl font-bold text-gray-900">{{ moderationStore.stats?.pending ?? '—' }}</div>
      </div>
      <div class="bg-white border border-gray-200 rounded-xl p-5">
        <div class="text-sm text-gray-600">{{ t('curator.stats.changesRequested') }}</div>
        <div class="text-3xl font-bold text-gray-900">{{ moderationStore.stats?.changes_requested ?? '—' }}</div>
      </div>
      <div class="bg-white border border-gray-200 rounded-xl p-5">
        <div class="text-sm text-gray-600">{{ t('curator.stats.flaggedOpen') }}</div>
        <div class="text-3xl font-bold text-gray-900">{{ moderationStore.stats?.flagged_open ?? '—' }}</div>
      </div>
      <div class="bg-white border border-gray-200 rounded-xl p-5">
        <div class="text-sm text-gray-600">{{ t('curator.stats.reviewedTotal') }}</div>
        <div class="text-3xl font-bold text-gray-900">{{ moderationStore.stats?.reviewed_total ?? '—' }}</div>
      </div>
    </div>

    <!-- D1: per-city workload for multi-city curators -->
    <section v-if="cityBreakdown.length > 1" class="mt-6 bg-white border border-gray-200 rounded-xl p-5">
      <h2 class="text-lg font-semibold text-gray-900 mb-3">{{ t('curator.byCity.title') }}</h2>
      <table class="min-w-full text-sm">
        <thead>
          <tr class="text-left text-xs font-semibold text-gray-600 uppercase tracking-wider">
            <th class="py-2 pr-4">{{ t('curator.byCity.city') }}</th>
            <th class="py-2 pr-4">{{ t('curator.stats.pending') }}</th>
            <th class="py-2 pr-4">{{ t('curator.stats.changesRequested') }}</th>
            <th class="py-2"></th>
          </tr>
        </thead>
        <tbody class="divide-y divide-gray-100">
          <tr v-for="c in cityBreakdown" :key="c.slug">
            <td class="py-2 pr-4 font-medium text-gray-900">{{ c.name }}</td>
            <td class="py-2 pr-4">{{ c.pending }}</td>
            <td class="py-2 pr-4">{{ c.changes_requested }}</td>
            <td class="py-2 text-right">
              <button
                class="text-xs font-medium text-primary-700 hover:text-primary-900 underline"
                :disabled="!cityStore.isAllCities && cityStore.activeCity?.slug === c.slug"
                @click="cityStore.setCity(c.slug)"
              >
                {{ t('curator.byCity.moderate') }}
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </section>
  </div>
</template>

