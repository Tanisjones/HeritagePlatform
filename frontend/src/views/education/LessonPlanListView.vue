<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { lessonPlanService, curriculumService } from '@/services/api'
import { useCityStore } from '@/stores/city'
import { useCityPath } from '@/composables/useCityPath'
import { useAsyncAction } from '@/composables/useAsyncAction'
import { unwrapResults } from '@/utils/pagination'
import { useConfirm, useToast } from '@/composables/useDialogs'
import type { LessonPlan, LessonPlanAdaptation, CurriculumStandard } from '@/types/heritage'
import type { City } from '@/types/city'
import AppButton from '@/components/common/AppButton.vue'
import AppCard from '@/components/common/AppCard.vue'
import ErrorBanner from '@/components/common/ErrorBanner.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import BaseSpinner from '@/components/common/BaseSpinner.vue'

const router = useRouter()
const { t } = useI18n()
const { confirm } = useConfirm()
const toast = useToast()
const cityStore = useCityStore()
const { citySegment } = useCityPath()
const { loading, error, run } = useAsyncAction()

const plans = ref<LessonPlan[]>([])

// A.6 / A.3 — discovery filters: by curriculum standard, and "only mine".
const standardFilter = ref('')
const mineOnly = ref(false)
const standardsCatalog = ref<CurriculumStandard[]>([])
const standardsBySubject = computed(() => {
  const groups = new Map<string, CurriculumStandard[]>()
  for (const std of standardsCatalog.value) {
    const key = std.subject || '—'
    if (!groups.has(key)) groups.set(key, [])
    groups.get(key)!.push(std)
  }
  return groups
})
const hasFilters = computed(() => Boolean(standardFilter.value || mineOnly.value))

async function load() {
  await run(async () => {
    const params: Record<string, any> = {}
    if (standardFilter.value) params.standard = standardFilter.value
    if (mineOnly.value) params.mine = 1
    const res = await lessonPlanService.list(params)
    plans.value = unwrapResults<LessonPlan>(res.data)
  })
}

async function loadStandards() {
  try {
    standardsCatalog.value = unwrapResults<CurriculumStandard>(
      (await curriculumService.standards()).data,
    )
  } catch {
    standardsCatalog.value = []
  }
}

watch([standardFilter, mineOnly], load)

function createNew() {
  router.push({ name: 'lesson-plan-new' })
}

function edit(plan: LessonPlan) {
  router.push({ name: 'lesson-plan-edit', params: { id: plan.id } })
}

// A.7 — duplicate, optionally adapting the copy for another city.
const dupPlan = ref<LessonPlan | null>(null)
const dupCity = ref('')
const duplicating = ref(false)

function cityName(slug: string): string {
  return cityStore.cities.find((c: City) => c.slug === slug)?.name ?? slug
}

function cityOptionLabel(c: City): string {
  return c.slug === dupPlan.value?.city?.slug
    ? `${c.name} (${t('lessonPlans.duplicateTo.sameCity')})`
    : c.name
}

function openDuplicate(plan: LessonPlan) {
  if (cityStore.cities.length <= 1) {
    void runDuplicate(plan, null)
    return
  }
  dupPlan.value = plan
  dupCity.value = plan.city?.slug || cityStore.activeCity?.slug || ''
}

async function runDuplicate(plan: LessonPlan, citySlug: string | null) {
  duplicating.value = true
  try {
    const adapting = Boolean(citySlug && citySlug !== plan.city?.slug)
    const res = await lessonPlanService.duplicate(plan.id, adapting ? { city: citySlug! } : undefined)
    const adaptation = (res.data as { adaptation?: LessonPlanAdaptation }).adaptation
    if (adaptation) {
      toast.success(
        t('lessonPlans.duplicateTo.adapted', {
          city: cityName(adaptation.city),
          relinked: adaptation.relinked,
          dropped: adaptation.dropped,
        }),
        6000,
      )
    } else {
      toast.success(t('lessonPlans.duplicated'))
    }
    dupPlan.value = null
    router.push({ name: 'lesson-plan-edit', params: { id: res.data.id } })
  } catch {
    toast.error(t('common.errorGeneric'))
  } finally {
    duplicating.value = false
  }
}

async function remove(plan: LessonPlan) {
  if (!(await confirm({ message: t('lessonPlans.confirmDelete'), danger: true }))) return
  try {
    await lessonPlanService.delete(plan.id)
    plans.value = plans.value.filter((p) => p.id !== plan.id)
  } catch {
    toast.error(t('common.errorGeneric'))
  }
}

const statusClass: Record<string, string> = {
  draft: 'bg-gray-100 text-gray-700',
  review: 'bg-yellow-100 text-yellow-800',
  published: 'bg-secondary-100 text-secondary-800',
  archived: 'bg-gray-100 text-gray-500',
}

onMounted(() => {
  load()
  loadStandards()
})
</script>

<template>
  <div class="max-w-6xl mx-auto p-5 space-y-5">
    <div class="flex items-center justify-between gap-4">
      <div>
        <h1 class="text-3xl font-display font-bold text-gray-900">{{ t('lessonPlans.title') }}</h1>
        <p class="mt-1 text-gray-600">{{ t('lessonPlans.subtitle') }}</p>
      </div>
      <AppButton @click="createNew">{{ t('lessonPlans.create') }}</AppButton>
    </div>

    <!-- A.6/A.3: filters -->
    <div class="flex flex-wrap items-center gap-3">
      <select
        v-if="standardsCatalog.length"
        v-model="standardFilter"
        class="rounded-lg border-gray-300 text-sm focus:border-primary-500 focus:ring-primary-500"
      >
        <option value="">{{ t('lessonPlans.filters.allStandards') }}</option>
        <optgroup v-for="[subject, group] in standardsBySubject" :key="subject" :label="subject">
          <option v-for="std in group" :key="std.id" :value="std.code">
            {{ std.code }} · {{ std.grade_level }}
          </option>
        </optgroup>
      </select>
      <label class="inline-flex items-center gap-2 text-sm text-gray-700">
        <input
          v-model="mineOnly"
          type="checkbox"
          class="rounded border-gray-300 text-primary-600 focus:ring-primary-500"
        />
        {{ t('lessonPlans.filters.mineOnly') }}
      </label>
    </div>

    <ErrorBanner :message="error" @retry="load" />

    <div v-if="loading" class="flex justify-center py-16">
      <BaseSpinner class="h-8 w-8 text-primary-600" />
    </div>

    <EmptyState
      v-else-if="plans.length === 0 && !hasFilters"
      :title="t('lessonPlans.empty.title')"
      :description="t('lessonPlans.empty.description')"
    >
      <AppButton @click="createNew">{{ t('lessonPlans.create') }}</AppButton>
    </EmptyState>

    <p v-else-if="plans.length === 0" class="text-center text-gray-500 py-10">
      {{ t('lessonPlans.filters.noMatches') }}
    </p>

    <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
      <AppCard v-for="plan in plans" :key="plan.id" hoverable>
        <div class="flex items-start justify-between gap-2">
          <h3 class="font-semibold text-gray-900">{{ plan.title }}</h3>
          <span class="px-2 py-0.5 rounded-full text-xs font-medium" :class="statusClass[plan.status]">
            {{ t(`lessonPlans.status.${plan.status}`) }}
          </span>
        </div>
        <p v-if="plan.summary" class="mt-2 text-sm text-gray-600 line-clamp-2">{{ plan.summary }}</p>
        <div class="mt-3 flex flex-wrap gap-2 text-xs text-gray-500">
          <span v-if="plan.subject">{{ plan.subject }}</span>
          <span v-if="plan.grade_level">· {{ t('lessonPlans.gradeShort') }} {{ plan.grade_level }}</span>
          <span>· {{ plan.activities.length }} {{ t('lessonPlans.activitiesCount') }}</span>
        </div>
        <div v-if="plan.standards_detail?.length" class="mt-2 flex flex-wrap gap-1.5">
          <span
            v-for="std in plan.standards_detail.slice(0, 4)"
            :key="std.id"
            class="px-2 py-0.5 rounded-full bg-primary-50 text-primary-700 border border-primary-100 text-xs"
            :title="std.description"
          >{{ std.code }}</span>
        </div>
        <div class="mt-4 flex gap-2 flex-wrap">
          <AppButton size="sm" @click="edit(plan)">{{ t('common.edit') }}</AppButton>
          <AppButton
            v-if="plan.status === 'published'"
            size="sm"
            variant="ghost"
            @click="router.push({ name: 'lesson-plan-detail', params: { id: plan.id, citySlug: plan.city?.slug || citySegment } })"
          >
            {{ t('lessonPlans.viewPublic') }}
          </AppButton>
          <AppButton size="sm" variant="ghost" @click="openDuplicate(plan)">{{ t('lessonPlans.duplicate') }}</AppButton>
          <AppButton size="sm" variant="ghost" class="!text-red-600" @click="remove(plan)">{{ t('common.delete') }}</AppButton>
        </div>
      </AppCard>
    </div>

    <!-- A.7: duplicate-and-adapt dialog -->
    <div
      v-if="dupPlan"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
      @click.self="dupPlan = null"
    >
      <div class="bg-white rounded-xl shadow-xl max-w-md w-full p-5" role="dialog" aria-modal="true">
        <h3 class="text-lg font-semibold text-gray-900">{{ t('lessonPlans.duplicateTo.title') }}</h3>
        <p class="mt-1 text-sm text-gray-600">{{ dupPlan.title }}</p>
        <label class="block text-sm font-medium text-gray-700 mt-4 mb-1">
          {{ t('lessonPlans.duplicateTo.targetCity') }}
        </label>
        <select v-model="dupCity" class="w-full rounded-lg border-gray-300 focus:border-primary-500 focus:ring-primary-500">
          <option v-for="c in cityStore.cities" :key="c.slug" :value="c.slug">{{ cityOptionLabel(c) }}</option>
        </select>
        <p class="mt-2 text-xs text-gray-500">{{ t('lessonPlans.duplicateTo.help') }}</p>
        <div class="mt-5 flex justify-end gap-2">
          <AppButton variant="ghost" @click="dupPlan = null">{{ t('common.cancel') }}</AppButton>
          <AppButton :loading="duplicating" @click="runDuplicate(dupPlan, dupCity)">
            {{ t('lessonPlans.duplicate') }}
          </AppButton>
        </div>
      </div>
    </div>
  </div>
</template>
