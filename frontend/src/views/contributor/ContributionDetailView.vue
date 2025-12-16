<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useContributionsStore } from '@/stores/contributions'
import ContributionFeedbackCard from '@/components/contributor/ContributionFeedbackCard.vue'

const route = useRoute()
const router = useRouter()
const id = computed(() => route.params.id as string)

const authStore = useAuthStore()
const contributionsStore = useContributionsStore()

onMounted(async () => {
  if (!authStore.isAuthenticated) return
  await Promise.all([contributionsStore.fetchContribution(id.value), contributionsStore.fetchFeedback(id.value)])
})
</script>

<template>
  <div class="container mx-auto px-4 py-8 space-y-4">
    <div class="flex items-start justify-between gap-4">
      <div>
        <button class="text-sm text-gray-600 hover:text-gray-900" @click="router.push('/my-contributions')">
          ← Back
        </button>
        <h1 class="text-3xl font-bold text-gray-900 mt-2">Contribution</h1>
      </div>
      <button
        class="px-4 py-2 rounded-lg bg-primary-600 text-white hover:bg-primary-700"
        @click="router.push(`/my-contributions/${id}/edit`)"
        :disabled="!authStore.isAuthenticated"
      >
        Edit
      </button>
    </div>

    <div v-if="!authStore.isAuthenticated" class="bg-white border border-gray-200 rounded-xl p-6">
      <h2 class="text-xl font-semibold text-gray-900">Login required</h2>
      <p class="text-gray-600 mt-1">Please log in to view your contribution.</p>
    </div>

    <template v-else>
      <ContributionFeedbackCard :feedback="contributionsStore.currentFeedback" />

      <section v-if="contributionsStore.currentContribution" class="bg-white border border-gray-200 rounded-xl p-5">
        <h2 class="text-lg font-semibold text-gray-900 mb-2">
          {{ (contributionsStore.currentContribution as any).title }}
        </h2>
        <div class="text-sm text-gray-700 whitespace-pre-wrap">
          {{ (contributionsStore.currentContribution as any).description }}
        </div>
      </section>
    </template>
  </div>
</template>

