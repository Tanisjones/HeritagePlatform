<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import api from '@/services/api'
import { useAuthStore } from '@/stores/auth'
import { useContributionsStore } from '@/stores/contributions'
import ContributionFeedbackCard from '@/components/contributor/ContributionFeedbackCard.vue'
import type { Parish, HeritageType, HeritageCategory } from '@/types/heritage'

const route = useRoute()
const router = useRouter()
const { t } = useI18n()
const id = computed(() => route.params.id as string)

// Same catalog the wizard offers — the model field is a choices field, so a
// free-text input here could only produce 400s.
const historicalPeriods = ['pre-columbian', 'colonial', 'republican', 'contemporary', 'unknown']

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
          ← {{ t('common.back') }}
        </button>
        <h1 class="text-3xl font-bold text-gray-900 mt-2">{{ t('myContributions.editTitle') }}</h1>
      </div>
      <div class="flex gap-2">
        <button class="px-4 py-2 rounded-lg border border-gray-200 hover:bg-gray-50" @click="save" :disabled="contributionsStore.loading">
          {{ t('myContributions.edit.save') }}
        </button>
        <button
          class="px-4 py-2 rounded-lg bg-primary-600 text-white hover:bg-primary-700 disabled:opacity-50"
          :disabled="contributionsStore.loading || !canResubmit"
          @click="resubmit"
        >
          {{ t('myContributions.edit.resubmit') }}
        </button>
      </div>
    </div>

    <div v-if="!authStore.isAuthenticated" class="bg-white border border-gray-200 rounded-xl p-6">
      <h2 class="text-xl font-semibold text-gray-900">{{ t('myContributions.loginRequiredTitle') }}</h2>
      <p class="text-gray-600 mt-1">{{ t('myContributions.loginRequiredText') }}</p>
    </div>

    <template v-else>
      <ContributionFeedbackCard :feedback="contributionsStore.currentFeedback" />

      <div v-if="contributionsStore.error" class="bg-red-50 border border-red-200 text-red-800 px-4 py-3 rounded-lg">
        {{ contributionsStore.error }}
      </div>

      <section class="bg-white border border-gray-200 rounded-xl p-5">
        <h2 class="text-lg font-semibold text-gray-900 mb-4">{{ t('contribution.steps.2') }}</h2>

        <div v-if="loadingMeta" class="text-sm text-gray-600">{{ t('myContributions.loading') }}</div>

        <div class="grid grid-cols-1 gap-4">
          <div>
            <label class="block text-sm font-semibold text-gray-700 mb-1">{{ t('contribution.step2.fields.title') }}</label>
            <input v-model="form.title" class="w-full rounded-lg border-gray-300" />
          </div>
          <div>
            <label class="block text-sm font-semibold text-gray-700 mb-1">{{ t('contribution.step2.fields.description') }}</label>
            <textarea v-model="form.description" rows="4" class="w-full rounded-lg border-gray-300" />
          </div>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label class="block text-sm font-semibold text-gray-700 mb-1">{{ t('contribution.step2.fields.heritageType') }}</label>
              <select v-model="form.heritage_type" class="w-full rounded-lg border-gray-300">
                <option :value="null">{{ t('contribution.step2.fields.selectType') }}</option>
                <option v-for="ht in heritageTypes" :key="ht.id" :value="ht.id">{{ ht.name }}</option>
              </select>
            </div>
            <div>
              <label class="block text-sm font-semibold text-gray-700 mb-1">{{ t('contribution.step2.fields.category') }}</label>
              <select v-model="form.heritage_category" class="w-full rounded-lg border-gray-300">
                <option :value="null">{{ t('contribution.step2.fields.selectCategory') }}</option>
                <option v-for="c in heritageCategories" :key="c.id" :value="c.id">{{ c.name }}</option>
              </select>
            </div>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label class="block text-sm font-semibold text-gray-700 mb-1">{{ t('contribution.step3.fields.parish') }}</label>
              <select v-model="form.parish" class="w-full rounded-lg border-gray-300">
                <option :value="null">{{ t('contribution.step3.fields.selectParish') }}</option>
                <option v-for="p in parishes" :key="p.id" :value="p.id">{{ p.name }}</option>
              </select>
            </div>
            <div>
              <label class="block text-sm font-semibold text-gray-700 mb-1">{{ t('contribution.step3.fields.address') }}</label>
              <input v-model="form.address" class="w-full rounded-lg border-gray-300" />
            </div>
          </div>

          <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label class="block text-sm font-semibold text-gray-700 mb-1">{{ t('contribution.step4.fields.historicalPeriod') }}</label>
              <!-- Choices field on the model — a select, not free text (a typo would 400). -->
              <select v-model="form.historical_period" class="w-full rounded-lg border-gray-300">
                <option value="">{{ t('contribution.step4.fields.selectPeriod') }}</option>
                <option v-for="p in historicalPeriods" :key="p" :value="p">{{ p }}</option>
              </select>
            </div>
            <div>
              <label class="block text-sm font-semibold text-gray-700 mb-1">{{ t('contribution.step4.fields.externalUrl') }}</label>
              <input v-model="form.external_registry_url" class="w-full rounded-lg border-gray-300" />
            </div>
          </div>
        </div>
      </section>
    </template>
  </div>
</template>

