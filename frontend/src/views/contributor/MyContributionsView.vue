<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useContributionsStore } from '@/stores/contributions'
import ContributionStatusCard from '@/components/contributor/ContributionStatusCard.vue'
import ContributionStatsCard from '@/components/contributor/ContributionStatsCard.vue'

const router = useRouter()
const authStore = useAuthStore()
const contributionsStore = useContributionsStore()

const statusFilter = ref<string>('all')

const filtered = computed(() => {
  if (statusFilter.value === 'all') return contributionsStore.myContributions
  return contributionsStore.myContributions.filter((c: any) => c.status === statusFilter.value)
})

const stats = computed(() => {
  const list = contributionsStore.myContributions
  const count = (s: string) => list.filter((c: any) => c.status === s).length
  return {
    total: list.length,
    pending: count('pending'),
    changesRequested: count('changes_requested'),
    published: count('published'),
    rejected: count('rejected'),
  }
})

async function refresh() {
  await contributionsStore.fetchMyContributions()
}

async function openFeedback(id: string) {
  router.push(`/my-contributions/${id}`)
}

onMounted(async () => {
  if (authStore.isAuthenticated) {
    await refresh()
  }
})
</script>

<template>
  <div class="container mx-auto px-4 py-8 space-y-4">
    <div class="flex items-center justify-between">
      <h1 class="text-3xl font-bold text-gray-900">My Contributions</h1>
      <button
        class="px-4 py-2 rounded-lg border border-gray-200 hover:bg-gray-50"
        @click="refresh"
      >
        Refresh
      </button>
    </div>

    <div v-if="!authStore.isAuthenticated" class="bg-white border border-gray-200 rounded-xl p-6">
      <h2 class="text-xl font-semibold text-gray-900">Login required</h2>
      <p class="text-gray-600 mt-1">Please log in to view your contributions.</p>
    </div>

    <template v-else>
      <ContributionStatsCard v-bind="stats" />

      <div class="flex items-end justify-between gap-3">
        <div class="w-full md:w-64">
          <label class="block text-sm font-semibold text-gray-700 mb-1">Status</label>
          <select v-model="statusFilter" class="w-full rounded-lg border-gray-300">
            <option value="all">All</option>
            <option value="pending">Pending</option>
            <option value="changes_requested">Changes requested</option>
            <option value="published">Published</option>
            <option value="rejected">Rejected</option>
          </select>
        </div>
      </div>

      <div v-if="contributionsStore.error" class="bg-red-50 border border-red-200 text-red-800 px-4 py-3 rounded-lg">
        {{ contributionsStore.error }}
      </div>

      <div v-if="contributionsStore.loading" class="text-gray-600">Loading…</div>

      <div v-else class="grid grid-cols-1 gap-4">
        <ContributionStatusCard
          v-for="c in filtered"
          :key="c.id"
          :contribution="c"
          @feedback="openFeedback"
          @edit="(id) => router.push(`/my-contributions/${id}/edit`)"
        />
        <div v-if="filtered.length === 0" class="text-sm text-gray-600">No contributions.</div>
      </div>
    </template>
  </div>
</template>

