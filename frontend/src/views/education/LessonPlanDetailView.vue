<script setup lang="ts">
/**
 * P.5 — public "lesson sheet" for a published + public LessonPlan.
 *
 * Read-only presentation of a plan's objectives, curriculum alignment, audience,
 * total time, and its ordered activities (each with type badge, instructions, and
 * a link to any bound heritage item / route / resource). Reachable by anyone for a
 * published-public plan; the backend get_queryset enforces visibility, so a private
 * plan 404s here for non-owners. Closes the F2.b.5 "pedagogical sheet" gap.
 */
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { lessonPlanService } from '@/services/api'
import { useAsyncAction } from '@/composables/useAsyncAction'
import type { LessonPlan, LessonActivity } from '@/types/heritage'
import ErrorBanner from '@/components/common/ErrorBanner.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import BaseSpinner from '@/components/common/BaseSpinner.vue'

const route = useRoute()
const router = useRouter()
const { t } = useI18n()
const { loading, error, run } = useAsyncAction()

const plan = ref<LessonPlan | null>(null)

const orderedActivities = computed<LessonActivity[]>(() =>
  (plan.value?.activities || []).slice().sort((a, b) => a.order - b.order),
)

const totalMinutes = computed(() => {
  const explicit = plan.value?.estimated_total_minutes
  if (explicit != null) return explicit
  const sum = orderedActivities.value.reduce((acc, a) => acc + (a.duration_minutes || 0), 0)
  return sum > 0 ? sum : null
})

async function load() {
  await run(async () => {
    const res = await lessonPlanService.get(String(route.params.id))
    plan.value = res.data as LessonPlan
  })
}

/** Resolve a link target for an activity's bound content, if any. */
function activityLink(a: LessonActivity): { label: string; to: string } | null {
  if (a.heritage_item)
    return { label: a.heritage_item_title || t('lessonPlans.content.linkedHeritage'), to: `/heritage/${a.heritage_item}` }
  if (a.route) return { label: a.route_title || t('lessonPlans.content.linkedRoute'), to: `/routes/${a.route}` }
  if (a.educational_resource != null)
    return { label: a.educational_resource_title || t('lessonPlans.content.linkedResource'), to: `/education/${a.educational_resource}` }
  return null
}

onMounted(load)
</script>

<template>
  <div class="max-w-4xl mx-auto p-5">
    <ErrorBanner :message="error" @retry="load" />

    <div v-if="loading" class="flex justify-center py-16"><BaseSpinner class="h-8 w-8 text-primary-600" /></div>

    <EmptyState
      v-else-if="!plan"
      :title="t('lessonPlans.detail.notFoundTitle')"
      :message="t('lessonPlans.detail.notFoundMessage')"
    />

    <template v-else>
      <!-- header -->
      <header class="mb-6">
        <button class="text-sm text-primary-600 hover:underline mb-2" @click="router.back()">
          ← {{ t('common.back') }}
        </button>
        <h1 class="text-3xl font-display font-bold text-gray-900">{{ plan.title }}</h1>
        <p v-if="plan.summary" class="mt-2 text-gray-700">{{ plan.summary }}</p>
        <div class="mt-3 flex flex-wrap gap-2 text-sm">
          <span v-if="plan.subject" class="px-2 py-0.5 rounded-full bg-neutral-100 text-neutral-700">{{ plan.subject }}</span>
          <span v-if="plan.grade_level" class="px-2 py-0.5 rounded-full bg-neutral-100 text-neutral-700">{{ t('lessonPlans.detail.grade') }}: {{ plan.grade_level }}</span>
          <span v-if="plan.audience" class="px-2 py-0.5 rounded-full bg-neutral-100 text-neutral-700">{{ plan.audience }}</span>
          <span v-if="totalMinutes != null" class="px-2 py-0.5 rounded-full bg-primary-100 text-primary-800">{{ totalMinutes }} {{ t('lessonPlans.fields.minutes') }}</span>
        </div>
      </header>

      <!-- objectives + curriculum -->
      <section v-if="(plan.objectives && plan.objectives.length) || plan.curriculum_alignment" class="bg-white border border-gray-200 rounded-xl p-5 mb-6">
        <div v-if="plan.objectives && plan.objectives.length">
          <h2 class="text-lg font-semibold text-gray-900 mb-2">{{ t('lessonPlans.detail.objectives') }}</h2>
          <ul class="list-disc list-inside space-y-1 text-gray-700">
            <li v-for="(obj, i) in plan.objectives" :key="i">{{ obj }}</li>
          </ul>
        </div>
        <div v-if="plan.curriculum_alignment" class="mt-4 text-sm text-gray-600">
          <span class="font-medium">{{ t('lessonPlans.fields.curriculum') }}:</span> {{ plan.curriculum_alignment }}
        </div>
      </section>

      <!-- activity sequence -->
      <section>
        <h2 class="text-xl font-semibold text-gray-900 mb-3">{{ t('lessonPlans.activities') }}</h2>
        <ol class="space-y-3">
          <li
            v-for="(a, index) in orderedActivities"
            :key="a.id || index"
            class="bg-white border border-gray-200 rounded-xl p-5"
          >
            <div class="flex items-center gap-3 mb-2">
              <span class="flex-shrink-0 w-7 h-7 rounded-full bg-primary-600 text-white text-sm flex items-center justify-center">{{ index + 1 }}</span>
              <h3 class="font-semibold text-gray-900">{{ a.title }}</h3>
              <span class="px-2 py-0.5 rounded-full bg-secondary-100 text-secondary-800 text-xs">{{ t(`lessonPlans.activityTypes.${a.activity_type}`) }}</span>
              <span v-if="a.duration_minutes" class="ml-auto text-xs text-gray-400">{{ a.duration_minutes }} {{ t('lessonPlans.fields.minutes') }}</span>
            </div>
            <!-- instructions are sanitized server-side (nh3); safe to render as HTML -->
            <div v-if="a.instructions" class="prose prose-sm max-w-none text-gray-700" v-html="a.instructions"></div>
            <div v-if="activityLink(a)" class="mt-3">
              <RouterLink :to="activityLink(a)!.to" class="inline-flex items-center gap-1 text-sm text-primary-600 hover:underline">
                🔗 {{ activityLink(a)!.label }}
              </RouterLink>
            </div>
            <p v-if="a.materials" class="mt-2 text-xs text-gray-500">{{ t('lessonPlans.detail.materials') }}: {{ a.materials }}</p>
          </li>
        </ol>
        <div v-if="orderedActivities.length === 0" class="text-center text-gray-500 py-8 border border-dashed border-gray-200 rounded-lg">
          {{ t('lessonPlans.noActivities') }}
        </div>
      </section>
    </template>
  </div>
</template>
