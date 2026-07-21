<script setup lang="ts">
/**
 * A.4 — "modo clase": a projector-friendly, print-friendly rendering of a
 * lesson plan. On screen it plays as big-type slides (overview → one step per
 * activity → evaluation criteria); in print it lays out the whole plan as a
 * compact one-pager handout. Same visibility rules as the public ficha —
 * the backend 404s plans the caller can't see.
 */
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { lessonPlanService } from '@/services/api'
import { useAsyncAction } from '@/composables/useAsyncAction'
import { useCityPath } from '@/composables/useCityPath'
import type { LessonPlan, LessonActivity, Rubric } from '@/types/heritage'
import ErrorBanner from '@/components/common/ErrorBanner.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import BaseSpinner from '@/components/common/BaseSpinner.vue'

const route = useRoute()
const router = useRouter()
const { t } = useI18n()
const { cityPathFor } = useCityPath()
const { loading, error, run } = useAsyncAction()

const plan = ref<LessonPlan | null>(null)
const current = ref(0)

const orderedActivities = computed<LessonActivity[]>(() =>
  (plan.value?.activities || []).slice().sort((a, b) => a.order - b.order),
)

const totalMinutes = computed(() => {
  const explicit = plan.value?.estimated_total_minutes
  if (explicit != null) return explicit
  const sum = orderedActivities.value.reduce((acc, a) => acc + (a.duration_minutes || 0), 0)
  return sum > 0 ? sum : null
})

/** Every non-empty materials note across the plan (for the overview checklist). */
const allMaterials = computed(() =>
  orderedActivities.value
    .map((a) => (a.materials || '').trim())
    .filter(Boolean),
)

type Slide =
  | { kind: 'overview' }
  | { kind: 'activity'; activity: LessonActivity; step: number }
  | { kind: 'rubrics'; rubrics: Rubric[] }

const slides = computed<Slide[]>(() => {
  const list: Slide[] = [{ kind: 'overview' }]
  orderedActivities.value.forEach((activity, i) => list.push({ kind: 'activity', activity, step: i + 1 }))
  if (plan.value?.rubrics?.length) list.push({ kind: 'rubrics', rubrics: plan.value.rubrics })
  return list
})

function next() {
  if (current.value < slides.value.length - 1) current.value += 1
}
function prev() {
  if (current.value > 0) current.value -= 1
}

function onKey(e: KeyboardEvent) {
  if (e.key === 'ArrowRight' || e.key === 'PageDown' || e.key === ' ') {
    e.preventDefault()
    next()
  } else if (e.key === 'ArrowLeft' || e.key === 'PageUp') {
    e.preventDefault()
    prev()
  }
}

/**
 * Resolve a link target for an activity's bound content, if any. The content
 * belongs to the plan's city, so link into that city rather than whichever
 * one the reader happens to be browsing — these links get copied to students.
 */
function activityLink(a: LessonActivity): { label: string; to: string } | null {
  const city = plan.value?.city?.slug
  if (a.heritage_item)
    return { label: a.heritage_item_title || t('lessonPlans.content.linkedHeritage'), to: cityPathFor(city, `/heritage/${a.heritage_item}`) }
  if (a.route) return { label: a.route_title || t('lessonPlans.content.linkedRoute'), to: cityPathFor(city, `/routes/${a.route}`) }
  if (a.educational_resource != null)
    return { label: a.educational_resource_title || t('lessonPlans.content.linkedResource'), to: cityPathFor(city, `/education/${a.educational_resource}`) }
  return null
}

function sortedCriteria(rubric: Rubric) {
  return [...(rubric.criteria || [])].sort((a, b) => a.order - b.order)
}

function printPage() {
  window.print()
}

async function load() {
  await run(async () => {
    const res = await lessonPlanService.get(String(route.params.id))
    plan.value = res.data as LessonPlan
  })
}

onMounted(() => {
  load()
  window.addEventListener('keydown', onKey)
})
onBeforeUnmount(() => window.removeEventListener('keydown', onKey))
</script>

<template>
  <div class="class-mode min-h-screen bg-gray-50">
    <div class="max-w-5xl mx-auto p-4 md:p-6">
      <ErrorBanner :message="error" @retry="load" class="print:hidden" />

      <div v-if="loading" class="flex justify-center py-24"><BaseSpinner class="h-8 w-8 text-primary-600" /></div>

      <EmptyState
        v-else-if="!plan"
        :title="t('lessonPlans.detail.notFoundTitle')"
        :description="t('lessonPlans.detail.notFoundMessage')"
        class="print:hidden"
      />

      <template v-else>
        <!-- top bar (screen only) -->
        <div class="flex items-center justify-between gap-3 mb-4 print:hidden">
          <button
            class="text-sm text-primary-600 hover:underline"
            @click="router.push({ name: 'lesson-plan-detail', params: { id: String(route.params.id) } })"
          >
            ← {{ t('lessonPlans.classMode.exit') }}
          </button>
          <p class="text-sm text-gray-500 truncate">{{ plan.title }}</p>
          <div class="flex items-center gap-2">
            <span class="text-xs text-gray-400 tabular-nums">
              {{ t('lessonPlans.classMode.step', { n: current + 1, total: slides.length }) }}
            </span>
            <button
              class="px-3 py-1.5 text-sm rounded-lg border border-gray-300 text-gray-700 hover:bg-gray-100"
              @click="printPage"
            >
              🖨 {{ t('lessonPlans.classMode.print') }}
            </button>
          </div>
        </div>

        <!-- progress (screen only) -->
        <div class="h-1.5 bg-gray-200 rounded-full mb-6 print:hidden">
          <div
            class="h-1.5 bg-primary-600 rounded-full transition-all"
            :style="{ width: `${((current + 1) / slides.length) * 100}%` }"
          ></div>
        </div>

        <!-- slides: on screen only the current one; in print, all of them -->
        <section
          v-for="(slide, i) in slides"
          :key="i"
          class="print:block print:break-inside-avoid print:border-0 print:shadow-none print:min-h-0 print:p-0 print:mb-6"
          :class="i === current ? 'block' : 'hidden'"
        >
          <!-- overview -->
          <div v-if="slide.kind === 'overview'" class="bg-white rounded-2xl shadow-sm border border-gray-200 p-8 md:p-12 min-h-[60vh] print:min-h-0 print:p-0 print:border-0 print:shadow-none">
            <p class="text-sm font-semibold uppercase tracking-wide text-primary-600">{{ t('lessonPlans.classMode.title') }}</p>
            <h1 class="text-3xl md:text-5xl print:text-2xl font-display font-bold text-gray-900 mt-2">{{ plan.title }}</h1>
            <p v-if="plan.summary" class="mt-4 text-lg md:text-xl print:text-base text-gray-600">{{ plan.summary }}</p>
            <div class="mt-5 flex flex-wrap gap-2 text-sm">
              <span v-if="plan.subject" class="px-3 py-1 rounded-full bg-neutral-100 text-neutral-700">{{ plan.subject }}</span>
              <span v-if="plan.grade_level" class="px-3 py-1 rounded-full bg-neutral-100 text-neutral-700">{{ t('lessonPlans.detail.grade') }}: {{ plan.grade_level }}</span>
              <span v-if="totalMinutes != null" class="px-3 py-1 rounded-full bg-primary-100 text-primary-800">⏱ {{ totalMinutes }} {{ t('lessonPlans.fields.minutes') }}</span>
              <span class="px-3 py-1 rounded-full bg-secondary-100 text-secondary-800">{{ orderedActivities.length }} {{ t('lessonPlans.activitiesCount') }}</span>
            </div>

            <div class="mt-8 grid grid-cols-1 md:grid-cols-2 print:grid-cols-2 gap-8">
              <div v-if="plan.objectives?.length">
                <h2 class="text-lg font-semibold text-gray-900 mb-2">{{ t('lessonPlans.detail.objectives') }}</h2>
                <ul class="list-disc list-inside space-y-1.5 text-gray-700 text-base md:text-lg print:text-sm">
                  <li v-for="(obj, oi) in plan.objectives" :key="oi">{{ obj }}</li>
                </ul>
              </div>
              <div>
                <h2 class="text-lg font-semibold text-gray-900 mb-2">{{ t('lessonPlans.classMode.agenda') }}</h2>
                <ol class="space-y-1.5 text-gray-700 text-base md:text-lg print:text-sm">
                  <li v-for="(a, ai) in orderedActivities" :key="a.id || ai" class="flex items-center gap-2">
                    <span class="flex-shrink-0 w-6 h-6 rounded-full bg-primary-600 text-white text-xs flex items-center justify-center">{{ ai + 1 }}</span>
                    <span class="truncate">{{ a.title || t(`lessonPlans.activityTypes.${a.activity_type}`) }}</span>
                    <span v-if="a.duration_minutes" class="ml-auto text-sm text-gray-400 tabular-nums">{{ a.duration_minutes }}′</span>
                  </li>
                </ol>
              </div>
            </div>

            <div v-if="allMaterials.length" class="mt-8 bg-amber-50 border border-amber-100 rounded-xl p-4 print:p-2">
              <h2 class="text-base font-semibold text-amber-900 mb-1.5">🧺 {{ t('lessonPlans.classMode.materials') }}</h2>
              <ul class="list-disc list-inside text-amber-900/90 space-y-1 text-sm">
                <li v-for="(m, mi) in allMaterials" :key="mi">{{ m }}</li>
              </ul>
            </div>
          </div>

          <!-- one activity per step -->
          <div v-else-if="slide.kind === 'activity'" class="bg-white rounded-2xl shadow-sm border border-gray-200 p-8 md:p-12 min-h-[60vh] print:min-h-0 print:p-0 print:border-0 print:shadow-none">
            <div class="flex items-center gap-4 flex-wrap">
              <span class="w-12 h-12 print:w-8 print:h-8 rounded-full bg-primary-600 text-white text-xl print:text-sm font-bold flex items-center justify-center">{{ slide.step }}</span>
              <span class="px-3 py-1 rounded-full bg-secondary-100 text-secondary-800 text-sm">{{ t(`lessonPlans.activityTypes.${slide.activity.activity_type}`) }}</span>
              <span v-if="slide.activity.duration_minutes" class="ml-auto text-lg print:text-sm text-gray-500 tabular-nums">⏱ {{ slide.activity.duration_minutes }} {{ t('lessonPlans.fields.minutes') }}</span>
            </div>
            <h2 class="text-2xl md:text-4xl print:text-lg font-display font-bold text-gray-900 mt-5">{{ slide.activity.title }}</h2>
            <!-- instructions are sanitized server-side (nh3); safe to render as HTML -->
            <div
              v-if="slide.activity.instructions"
              class="prose prose-lg print:prose-sm max-w-none text-gray-800 mt-5"
              v-html="slide.activity.instructions"
            ></div>
            <div v-if="slide.activity.materials" class="mt-6 bg-amber-50 border border-amber-100 rounded-xl p-4 print:p-2 text-amber-900 text-base print:text-sm">
              🧺 <span class="font-medium">{{ t('lessonPlans.detail.materials') }}:</span> {{ slide.activity.materials }}
            </div>
            <div class="mt-6 flex flex-wrap gap-3 items-center print:hidden">
              <RouterLink
                v-if="activityLink(slide.activity)"
                :to="activityLink(slide.activity)!.to"
                target="_blank"
                class="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-primary-50 border border-primary-100 text-primary-700 hover:bg-primary-100"
              >
                🔗 {{ activityLink(slide.activity)!.label }}
              </RouterLink>
              <span
                v-if="slide.activity.lom_general"
                class="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-secondary-50 border border-secondary-100 text-secondary-800"
              >
                ❓ {{ t('lessonPlans.content.quiz') }}: {{ slide.activity.lom_general_title || '' }}
                <template v-if="slide.activity.quiz_question_count != null">
                  ({{ t('lessonPlans.content.questionCount', slide.activity.quiz_question_count) }})
                </template>
              </span>
            </div>
          </div>

          <!-- evaluation criteria (rubrics) -->
          <div v-else class="bg-white rounded-2xl shadow-sm border border-gray-200 p-8 md:p-12 min-h-[60vh] print:min-h-0 print:p-0 print:border-0 print:shadow-none">
            <h2 class="text-2xl md:text-4xl print:text-lg font-display font-bold text-gray-900">{{ t('lessonPlans.detail.evaluation') }}</h2>
            <div v-for="rubric in slide.rubrics" :key="rubric.id" class="mt-6">
              <h3 class="text-lg md:text-xl print:text-base font-semibold text-gray-900">{{ rubric.title }}</h3>
              <p v-if="rubric.description" class="text-gray-600 mt-1">{{ rubric.description }}</p>
              <table class="w-full text-base print:text-xs mt-3">
                <thead>
                  <tr class="text-left text-gray-500 border-b border-gray-200">
                    <th class="py-2 font-medium">{{ t('lessonPlans.detail.criterion') }}</th>
                    <th class="py-2 font-medium text-right">{{ t('lessonPlans.detail.points') }}</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="c in sortedCriteria(rubric)" :key="c.id || c.label" class="border-b border-gray-100 last:border-0 align-top">
                    <td class="py-2 text-gray-800">
                      {{ c.label }}
                      <span v-if="c.levels?.length" class="block text-sm print:text-xs text-gray-500 mt-0.5">
                        <template v-for="(lvl, li) in c.levels" :key="li">
                          <span class="mr-3">{{ lvl.level }}<template v-if="lvl.points != null"> ({{ lvl.points }})</template><template v-if="lvl.descriptor">: {{ lvl.descriptor }}</template></span>
                        </template>
                      </span>
                    </td>
                    <td class="py-2 text-right tabular-nums">{{ c.max_points }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </section>

        <!-- prev / next (screen only) -->
        <div class="flex items-center justify-between mt-6 print:hidden">
          <button
            class="px-5 py-2.5 rounded-lg border border-gray-300 text-gray-700 hover:bg-gray-100 disabled:opacity-40"
            :disabled="current === 0"
            @click="prev"
          >
            ← {{ t('lessonPlans.classMode.prev') }}
          </button>
          <p class="text-xs text-gray-400 hidden md:block">{{ t('lessonPlans.classMode.keysHint') }}</p>
          <button
            class="px-5 py-2.5 rounded-lg bg-primary-600 text-white hover:bg-primary-700 disabled:opacity-40"
            :disabled="current === slides.length - 1"
            @click="next"
          >
            {{ t('lessonPlans.classMode.next') }} →
          </button>
        </div>
      </template>
    </div>
  </div>
</template>

<style scoped>
@media print {
  .class-mode {
    background: white;
  }
}
</style>
