<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '@/services/api'
import { useAuthStore } from '@/stores/auth'
import { useContributionsStore } from '@/stores/contributions'
import ContributionFeedbackCard from '@/components/contributor/ContributionFeedbackCard.vue'
import type { Parish, HeritageType, HeritageCategory } from '@/types/heritage'

const route = useRoute()
const router = useRouter()
const id = computed(() => route.params.id as string)

const authStore = useAuthStore()
const contributionsStore = useContributionsStore()

const parishes = ref<Parish[]>([])
const heritageTypes = ref<HeritageType[]>([])
const heritageCategories = ref<HeritageCategory[]>([])
const loadingMeta = ref(false)

const form = reactive({
  title: '',
  description: '',
  address: '',
  parish: null as number | null,
  heritage_type: null as number | null,
  heritage_category: null as number | null,
  historical_period: '',
  external_registry_url: '',
})

const canResubmit = computed(() => {
  const status = contributionsStore.currentFeedback?.status
  return status === 'rejected' || status === 'changes_requested'
})

async function loadMeta() {
  loadingMeta.value = true
  try {
    const [parishesRes, typesRes, categoriesRes] = await Promise.all([
      api.get('/parishes/'),
      api.get('/types/'),
      api.get('/categories/all/'),
    ])
    parishes.value = parishesRes.data.results ?? parishesRes.data
    heritageTypes.value = typesRes.data.results ?? typesRes.data
    heritageCategories.value = categoriesRes.data.results ?? categoriesRes.data
  } finally {
    loadingMeta.value = false
  }
}

async function load() {
  await Promise.all([contributionsStore.fetchContribution(id.value), contributionsStore.fetchFeedback(id.value), loadMeta()])

  const c: any = contributionsStore.currentContribution
  if (!c) return
  form.title = c.title ?? ''
  form.description = c.description ?? ''
  form.address = c.address ?? ''
  form.parish = c.parish?.id ?? null
  form.heritage_type = c.heritage_type?.id ?? null
  form.heritage_category = c.heritage_category?.id ?? null
  form.historical_period = c.historical_period ?? ''
  form.external_registry_url = c.external_registry_url ?? ''
}

async function save() {
  await contributionsStore.updateContribution(id.value, { ...form })
}

async function resubmit() {
  await contributionsStore.resubmit(id.value)
  router.push('/my-contributions')
}

onMounted(async () => {
  if (!authStore.isAuthenticated) return
  await load()
})
</script>

<template>
  <div class="container mx-auto px-4 py-8 space-y-4">
    <div class="flex items-start justify-between gap-4">
      <div>
        <button class="text-sm text-gray-600 hover:text-gray-900" @click="router.push('/my-contributions')">
          ← Back
        </button>
        <h1 class="text-3xl font-bold text-gray-900 mt-2">Edit Contribution</h1>
      </div>
      <div class="flex gap-2">
        <button class="px-4 py-2 rounded-lg border border-gray-200 hover:bg-gray-50" @click="save" :disabled="contributionsStore.loading">
          Save
        </button>
        <button
          class="px-4 py-2 rounded-lg bg-primary-600 text-white hover:bg-primary-700 disabled:opacity-50"
          :disabled="contributionsStore.loading || !canResubmit"
          @click="resubmit"
        >
          Resubmit
        </button>
      </div>
    </div>

    <div v-if="!authStore.isAuthenticated" class="bg-white border border-gray-200 rounded-xl p-6">
      <h2 class="text-xl font-semibold text-gray-900">Login required</h2>
      <p class="text-gray-600 mt-1">Please log in to edit your contribution.</p>
    </div>

    <template v-else>
      <ContributionFeedbackCard :feedback="contributionsStore.currentFeedback" />

      <div v-if="contributionsStore.error" class="bg-red-50 border border-red-200 text-red-800 px-4 py-3 rounded-lg">
        {{ contributionsStore.error }}
      </div>

      <section class="bg-white border border-gray-200 rounded-xl p-5">
        <h2 class="text-lg font-semibold text-gray-900 mb-4">General information</h2>

        <div v-if="loadingMeta" class="text-sm text-gray-600">Loading…</div>

        <div class="grid grid-cols-1 gap-4">
          <div>
            <label class="block text-sm font-semibold text-gray-700 mb-1">Title</label>
            <input v-model="form.title" class="w-full rounded-lg border-gray-300" />
          </div>
          <div>
            <label class="block text-sm font-semibold text-gray-700 mb-1">Description</label>
            <textarea v-model="form.description" rows="4" class="w-full rounded-lg border-gray-300" />
          </div>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label class="block text-sm font-semibold text-gray-700 mb-1">Heritage type</label>
              <select v-model="form.heritage_type" class="w-full rounded-lg border-gray-300">
                <option :value="null">Select</option>
                <option v-for="t in heritageTypes" :key="t.id" :value="t.id">{{ t.name }}</option>
              </select>
            </div>
            <div>
              <label class="block text-sm font-semibold text-gray-700 mb-1">Category</label>
              <select v-model="form.heritage_category" class="w-full rounded-lg border-gray-300">
                <option :value="null">Select</option>
                <option v-for="c in heritageCategories" :key="c.id" :value="c.id">{{ c.name }}</option>
              </select>
            </div>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label class="block text-sm font-semibold text-gray-700 mb-1">Parish</label>
              <select v-model="form.parish" class="w-full rounded-lg border-gray-300">
                <option :value="null">Select</option>
                <option v-for="p in parishes" :key="p.id" :value="p.id">{{ p.name }}</option>
              </select>
            </div>
            <div>
              <label class="block text-sm font-semibold text-gray-700 mb-1">Address</label>
              <input v-model="form.address" class="w-full rounded-lg border-gray-300" />
            </div>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label class="block text-sm font-semibold text-gray-700 mb-1">Historical period</label>
              <input v-model="form.historical_period" class="w-full rounded-lg border-gray-300" placeholder="e.g. colonial" />
            </div>
            <div>
              <label class="block text-sm font-semibold text-gray-700 mb-1">External registry URL</label>
              <input v-model="form.external_registry_url" class="w-full rounded-lg border-gray-300" />
            </div>
          </div>
        </div>
      </section>
    </template>
  </div>
</template>

