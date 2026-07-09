<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useCityStore } from '@/stores/city'
import { lessonPlanService, aiService, educationService, curriculumService, routeService } from '@/services/api'
import { useAsyncAction } from '@/composables/useAsyncAction'
import { useToast, useConfirm } from '@/composables/useDialogs'
import { useAiError } from '@/composables/useAiError'
import { useAIAvailability } from '@/services/aiAvailability'
import { extractApiError } from '@/utils/apiError'
import { saveBlob, readBlobError, slugifyFilename } from '@/utils/download'
import { unwrapResults } from '@/utils/pagination'
import type { LessonActivity, LessonActivityType, LessonPlan, LessonPlanWriteData, CurriculumStandard } from '@/types/heritage'
import AppButton from '@/components/common/AppButton.vue'
import AppInput from '@/components/common/AppInput.vue'
import ErrorBanner from '@/components/common/ErrorBanner.vue'
import BaseSpinner from '@/components/common/BaseSpinner.vue'
import AiActionButton from '@/components/common/AiActionButton.vue'
import ActivityContentPicker from '@/components/education/ActivityContentPicker.vue'
import QuizEditor from '@/components/education/QuizEditor.vue'

const route = useRoute()
const router = useRouter()
const { t } = useI18n()
const cityStore = useCityStore()
const toast = useToast()
const { confirm } = useConfirm()
const { applyAIError } = useAiError()
const { isAvailable: aiAvailable, refresh: refreshAi } = useAIAvailability()
const { loading, error, run } = useAsyncAction()
const saving = ref(false)
const saveError = ref<string | null>(null)

const planId = computed(() => (route.params.id ? String(route.params.id) : null))
const isNew = computed(() => !planId.value)

const ACTIVITY_TYPES: LessonActivityType[] = ['hook', 'explore', 'explain', 'practice', 'assess', 'reflect']
const APPROACHES = ['expository', 'inquiry', 'constructivist', 'project_based', 'collaborative', 'gamified']

const form = reactive<{
  title: string
  summary: string
  subject: string
  grade_level: string
  audience: string
  curriculum_alignment: string
  pedagogical_approach: string
  status: LessonPlan['status']
  visibility: LessonPlan['visibility']
  objectivesText: string
  activities: LessonActivity[]
  standards: string[]
  related_route: string | null
}>({
  title: '',
  summary: '',
  subject: '',
  grade_level: '',
  audience: '',
  curriculum_alignment: '',
  pedagogical_approach: '',
  status: 'draft',
  visibility: 'private',
  objectivesText: '',
  activities: [],
  standards: [],
  related_route: null,
})

// P.6: curriculum-standard catalog for the multi-select.
const standardsCatalog = ref<CurriculumStandard[]>([])

// A.1 — browsable standards picker: search + subject/grade filters over the
// catalog (client-side; the whole catalog is served unpaginated).
const stdSearch = ref('')
const stdSubject = ref('')
const stdGrade = ref('')
const GRADE_ORDER = ['Preparatoria', 'Básica elemental', 'Básica media', 'Básica superior', 'Bachillerato']
const stdSubjects = computed(() =>
  [...new Set(standardsCatalog.value.map((s) => s.subject).filter(Boolean))].sort() as string[],
)
const stdGrades = computed(() =>
  ([...new Set(standardsCatalog.value.map((s) => s.grade_level).filter(Boolean))] as string[]).sort((a, b) => {
    const ia = GRADE_ORDER.indexOf(a)
    const ib = GRADE_ORDER.indexOf(b)
    return (ia < 0 ? 99 : ia) - (ib < 0 ? 99 : ib) || a.localeCompare(b)
  }),
)
const filteredStandards = computed(() => {
  const q = stdSearch.value.trim().toLowerCase()
  return standardsCatalog.value.filter(
    (s) =>
      (!stdSubject.value || s.subject === stdSubject.value) &&
      (!stdGrade.value || s.grade_level === stdGrade.value) &&
      (!q || `${s.code} ${s.description} ${s.subject ?? ''}`.toLowerCase().includes(q)),
  )
})
const selectedStandards = computed(() => standardsCatalog.value.filter((s) => form.standards.includes(s.id)))
function toggleStandard(id: string) {
  const i = form.standards.indexOf(id)
  if (i >= 0) form.standards.splice(i, 1)
  else form.standards.push(id)
}

// A.3 — a plan can be seeded from a route (?route=<id>&title=<title>) and keeps
// a visible link to it. The title is fetched when we only have the id.
const relatedRouteTitle = ref('')
async function resolveRouteTitle() {
  if (!form.related_route || relatedRouteTitle.value) return
  try {
    relatedRouteTitle.value = String((await routeService.get(form.related_route)).data?.title ?? '')
  } catch {
    /* chip falls back to the id */
  }
}
function unlinkRoute() {
  form.related_route = null
  relatedRouteTitle.value = ''
}

function hydrate(plan: LessonPlan) {
  form.title = plan.title
  form.summary = plan.summary || ''
  form.subject = plan.subject || ''
  form.grade_level = plan.grade_level || ''
  form.audience = plan.audience || ''
  form.curriculum_alignment = plan.curriculum_alignment || ''
  form.pedagogical_approach = plan.pedagogical_approach || ''
  form.status = plan.status
  form.visibility = plan.visibility
  form.objectivesText = (plan.objectives || []).join('\n')
  form.standards = (plan.standards || []).slice()
  form.related_route = plan.related_route ?? null
  relatedRouteTitle.value = ''
  resolveRouteTitle()
  form.activities = (plan.activities || [])
    .slice()
    .sort((a, b) => a.order - b.order)
    .map((a) => ({ ...a }))
}

async function loadStandards() {
  try {
    standardsCatalog.value = unwrapResults<CurriculumStandard>((await curriculumService.standards()).data)
  } catch {
    standardsCatalog.value = []
  }
}

async function load() {
  refreshAi()
  loadStandards()
  if (isNew.value) {
    // A.3: "start from a route" — the teach hub links here with the route id.
    const qRoute = route.query.route ? String(route.query.route) : null
    if (qRoute) {
      form.related_route = qRoute
      relatedRouteTitle.value = route.query.title ? String(route.query.title) : ''
      resolveRouteTitle()
    }
    addActivity()
    return
  }
  await run(async () => {
    const res = await lessonPlanService.get(planId.value as string)
    hydrate(res.data as LessonPlan)
  })
}

function addActivity() {
  form.activities.push({
    order: form.activities.length,
    title: '',
    activity_type: 'explore',
    instructions: '',
    duration_minutes: null,
    heritage_item: null,
    route: null,
    educational_resource: null,
  })
}

function removeActivity(index: number) {
  form.activities.splice(index, 1)
  reindex()
}

/** Apply a content-picker selection to an activity (single-target binding). */
function onBindingChange(
  index: number,
  payload: {
    heritage_item: string | null
    route: string | null
    educational_resource: number | null
    lom_general: string | null
    picked_title?: string | null
  },
) {
  const a = form.activities[index]
  if (!a) return
  a.heritage_item = payload.heritage_item
  a.route = payload.route
  a.educational_resource = payload.educational_resource
  a.lom_general = payload.lom_general
  // Refresh the read-only titles: the picked row's title lands on the bound
  // field so the chip is right immediately; the rest are cleared until save.
  const title = payload.picked_title ?? null
  a.heritage_item_title = payload.heritage_item ? title : null
  a.route_title = payload.route ? title : null
  a.educational_resource_title = payload.educational_resource != null ? title : null
  a.lom_general_title = payload.lom_general ? title : null
  // A resolved quiz belongs to the OLD heritage item's LOM — reset it so it must be
  // re-resolved for the new binding (don't edit the wrong item's answer key).
  a._quizLomId = null
  a._quizError = ''
}

// --- native HTML5 drag-and-drop reorder (same approach as the route builder) ---
const dragIndex = ref<number | null>(null)
function onDragStart(index: number) {
  dragIndex.value = index
}
function onDrop(index: number) {
  if (dragIndex.value === null || dragIndex.value === index) return
  const [moved] = form.activities.splice(dragIndex.value, 1)
  if (moved) form.activities.splice(index, 0, moved)
  dragIndex.value = null
  reindex()
}
function reindex() {
  form.activities.forEach((a, i) => (a.order = i))
}

// --- quiz authoring for `assess` activities ---------------------------------
// A quiz lives on the LOMGeneral of the activity's bound heritage item. We resolve
// that id on demand and stash it ON THE ACTIVITY object (transient `_quiz*` fields)
// so the resolved editor travels with the activity through reorder/delete — keying
// by array index would bind the QuizEditor to the wrong activity after a splice.
async function openQuiz(activity: LessonActivity) {
  if (!activity.heritage_item) return
  activity._quizError = ''
  activity._quizResolving = true
  try {
    const res = await educationService.getByHeritageItem(activity.heritage_item)
    const lomId = res.data?.id
    if (lomId) activity._quizLomId = String(lomId)
    else activity._quizError = t('quiz.noLom')
  } catch {
    activity._quizError = t('quiz.noLom')
  } finally {
    activity._quizResolving = false
  }
}

const canSave = computed(() => form.title.trim().length > 0)

function buildPayload(): LessonPlanWriteData {
  const objectives = form.objectivesText
    .split('\n')
    .map((s) => s.trim())
    .filter(Boolean)
  return {
    title: form.title.trim(),
    summary: form.summary,
    subject: form.subject,
    grade_level: form.grade_level,
    audience: form.audience,
    curriculum_alignment: form.curriculum_alignment,
    pedagogical_approach: form.pedagogical_approach,
    // `status` is read-only on the write serializer — it changes only via the
    // submit/publish/archive actions, so we don't send it here.
    visibility: form.visibility,
    objectives,
    standards: form.standards,
    related_route: form.related_route ?? null,
    activities: form.activities.map((a, i) => ({
      ...(a.id ? { id: a.id } : {}),
      order: i,
      title: a.title,
      activity_type: a.activity_type,
      instructions: a.instructions || '',
      duration_minutes: a.duration_minutes ?? null,
      materials: a.materials || '',
      heritage_item: a.heritage_item ?? null,
      route: a.route ?? null,
      educational_resource: a.educational_resource ?? null,
      lom_general: a.lom_general ?? null,
    })),
  }
}

async function save(): Promise<LessonPlan | null> {
  if (!canSave.value) return null
  saving.value = true
  saveError.value = null
  try {
    const payload = buildPayload()
    const res = isNew.value
      ? await lessonPlanService.create(payload)
      : await lessonPlanService.update(planId.value as string, payload)
    toast.success(t('common.saved'))
    const plan = res.data as LessonPlan
    if (isNew.value) router.replace({ name: 'lesson-plan-edit', params: { id: plan.id } })
    hydrate(plan)
    return plan
  } catch (e: unknown) {
    saveError.value = extractApiError(e, t('common.errorSaving'))
    return null
  } finally {
    saving.value = false
  }
}

// --- AI: generate a draft that fills the editor (P.3) -----------------------
const aiLoading = ref(false)
const aiError = ref('')
async function generateWithAI() {
  const proceed =
    form.activities.length <= 1 && !form.activities.some((a) => a.title.trim())
      ? true
      : await confirm({
          title: t('lessonPlans.ai.replaceTitle'),
          message: t('lessonPlans.ai.replaceMessage'),
          confirmLabel: t('lessonPlans.ai.replaceConfirm'),
        })
  if (!proceed) return
  aiLoading.value = true
  aiError.value = ''
  try {
    const draft = await aiService.lessonPlanDraft({
      title: form.title,
      subject: form.subject,
      grade_level: form.grade_level,
      audience: form.audience,
      objectives: form.objectivesText.split('\n').map((s) => s.trim()).filter(Boolean),
    })
    if (draft.objectives?.length) form.objectivesText = draft.objectives.join('\n')
    form.activities = (draft.activities || []).map((a, i) => ({
      order: i,
      title: a.title,
      activity_type: a.activity_type,
      instructions: a.instructions || '',
      duration_minutes: a.duration_minutes ?? null,
      heritage_item: null,
      route: null,
      educational_resource: null,
      // Surface the AI's textual hint in materials so the teacher can find & bind it.
      materials: a.suggested_heritage_item_hint
        ? t('lessonPlans.ai.suggestedContent', { hint: a.suggested_heritage_item_hint })
        : '',
    }))
    toast.success(t('lessonPlans.ai.filled'))
  } catch (err) {
    applyAIError(err, aiError)
  } finally {
    aiLoading.value = false
  }
}

// --- state machine + export -------------------------------------------------
const acting = ref(false)
async function transition(kind: 'submit' | 'publish' | 'archive') {
  // Persist edits first so the transition acts on the latest content.
  const saved = await save()
  if (!saved) return
  acting.value = true
  try {
    const res = await lessonPlanService[kind](saved.id)
    hydrate(res.data as LessonPlan)
    toast.success(t(`lessonPlans.actions.${kind}Done`))
  } catch (e: unknown) {
    saveError.value = extractApiError(e, t('common.errorGeneric'))
  } finally {
    acting.value = false
  }
}

const exporting = ref(false)
async function exportScorm() {
  if (isNew.value) return
  exporting.value = true
  try {
    const res = await lessonPlanService.exportScorm(planId.value as string, 'scorm12')
    saveBlob(res.data as Blob, `${slugifyFilename(form.title || 'lesson-plan')}-scorm12.zip`)
  } catch (e: any) {
    saveError.value = await readBlobError(e, t('common.errorGeneric'))
  } finally {
    exporting.value = false
  }
}

const exportingPdf = ref(false)
async function exportPdf() {
  if (isNew.value) return
  exportingPdf.value = true
  try {
    const res = await lessonPlanService.exportPdf(planId.value as string)
    saveBlob(res.data as Blob, `${slugifyFilename(form.title || 'lesson-plan')}-lesson-plan.pdf`)
  } catch (e: any) {
    saveError.value = await readBlobError(e, t('common.errorGeneric'))
  } finally {
    exportingPdf.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="max-w-4xl mx-auto p-5 space-y-6">
    <div class="flex items-center justify-between gap-4 flex-wrap">
      <h1 class="text-3xl font-display font-bold text-gray-900">
        {{ isNew ? t('lessonPlans.newTitle') : t('lessonPlans.editTitle') }}
      </h1>
      <div class="flex gap-2 flex-wrap">
        <AppButton variant="ghost" @click="router.push({ name: 'lesson-plans' })">
          {{ t('common.cancel') }}
        </AppButton>
        <AppButton :loading="saving" :disabled="!canSave" @click="save">{{ t('common.save') }}</AppButton>
      </div>
    </div>

    <ErrorBanner :message="error" @retry="load" />
    <ErrorBanner :message="saveError" :retryable="false" dense />
    <ErrorBanner :message="aiError" :retryable="false" dense />

    <div v-if="loading" class="flex justify-center py-16">
      <BaseSpinner class="h-8 w-8 text-primary-600" />
    </div>

    <template v-else>
      <!-- Plan header -->
      <section class="bg-white rounded-lg shadow-sm p-5 space-y-4">
        <div class="flex items-start justify-between gap-3">
          <div class="flex-grow">
            <AppInput v-model="form.title" :label="t('lessonPlans.fields.title')" :placeholder="t('lessonPlans.fields.titlePlaceholder', { city: cityStore.activeCity?.name ?? 'Riobamba' })" />
          </div>
          <div class="pt-6">
            <AiActionButton
              :label="t('lessonPlans.ai.generate')"
              :loading-label="t('lessonPlans.ai.generating')"
              :loading="aiLoading"
              :available="aiAvailable"
              @click="generateWithAI"
            />
          </div>
        </div>
        <!-- A.3: plan seeded from / linked to a route -->
        <div v-if="form.related_route" class="flex items-center gap-2 text-sm flex-wrap">
          <span class="inline-flex items-center gap-1 px-2 py-1 rounded-full bg-secondary-100 text-secondary-800">
            <span class="font-medium">{{ t('lessonPlans.fields.relatedRoute') }}:</span>
            {{ relatedRouteTitle || form.related_route }}
          </span>
          <button type="button" class="text-xs text-red-600 hover:underline" @click="unlinkRoute">
            {{ t('lessonPlans.content.unlink') }}
          </button>
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('lessonPlans.fields.summary') }}</label>
          <textarea v-model="form.summary" rows="2" class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"></textarea>
        </div>
        <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
          <AppInput v-model="form.subject" :label="t('lessonPlans.fields.subject')" />
          <AppInput v-model="form.grade_level" :label="t('lessonPlans.fields.gradeLevel')" />
          <AppInput v-model="form.audience" :label="t('lessonPlans.fields.audience')" />
        </div>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <AppInput v-model="form.curriculum_alignment" :label="t('lessonPlans.fields.curriculum')" />
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('lessonPlans.fields.approach') }}</label>
            <select v-model="form.pedagogical_approach" class="w-full px-3 py-2 border border-gray-300 rounded-lg">
              <option value="">{{ t('lessonPlans.fields.approachNone') }}</option>
              <option v-for="a in APPROACHES" :key="a" :value="a">{{ t(`lessonPlans.approaches.${a}`) }}</option>
            </select>
          </div>
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('lessonPlans.fields.objectives') }}</label>
          <textarea v-model="form.objectivesText" rows="3" class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent" :placeholder="t('lessonPlans.fields.objectivesPlaceholder')"></textarea>
          <p class="mt-1 text-xs text-gray-500">{{ t('lessonPlans.fields.objectivesHelp') }}</p>
        </div>

        <!-- A.1: browsable curriculum-standards picker (search + subject/grade
             filters, full descriptions — teachers must see WHAT they align to) -->
        <div v-if="standardsCatalog.length">
          <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('lessonPlans.fields.standards') }}</label>

          <ul v-if="selectedStandards.length" class="mb-2 space-y-1">
            <li
              v-for="std in selectedStandards"
              :key="std.id"
              class="flex items-start gap-2 text-sm bg-primary-50 border border-primary-100 rounded-lg px-3 py-1.5"
            >
              <span class="font-semibold text-primary-800 whitespace-nowrap">{{ std.code }}</span>
              <span class="text-gray-700 flex-grow">{{ std.description }}</span>
              <span class="text-xs text-gray-500 whitespace-nowrap hidden md:inline">
                {{ std.subject }}<template v-if="std.grade_level"> · {{ std.grade_level }}</template>
              </span>
              <button
                type="button"
                class="text-red-600 text-xs hover:underline flex-shrink-0"
                :aria-label="t('lessonPlans.content.unlink')"
                @click="toggleStandard(std.id)"
              >✕</button>
            </li>
          </ul>
          <p v-else class="text-xs text-gray-500 mb-2">{{ t('lessonPlans.standardsPicker.empty') }}</p>

          <div class="grid grid-cols-1 md:grid-cols-3 gap-2 mb-2">
            <input
              v-model="stdSearch"
              type="search"
              class="px-3 py-1.5 border border-gray-300 rounded-lg text-sm"
              :placeholder="t('lessonPlans.standardsPicker.search')"
            />
            <select v-model="stdSubject" class="px-3 py-1.5 border border-gray-300 rounded-lg text-sm">
              <option value="">{{ t('lessonPlans.standardsPicker.allSubjects') }}</option>
              <option v-for="s in stdSubjects" :key="s" :value="s">{{ s }}</option>
            </select>
            <select v-model="stdGrade" class="px-3 py-1.5 border border-gray-300 rounded-lg text-sm">
              <option value="">{{ t('lessonPlans.standardsPicker.allGrades') }}</option>
              <option v-for="g in stdGrades" :key="g" :value="g">{{ g }}</option>
            </select>
          </div>

          <div class="border border-gray-200 rounded-lg max-h-56 overflow-y-auto divide-y divide-gray-100">
            <button
              v-for="std in filteredStandards"
              :key="std.id"
              type="button"
              class="w-full text-left px-3 py-2 flex gap-2 items-start hover:bg-primary-50 text-sm"
              :class="form.standards.includes(std.id) ? 'bg-primary-50/70' : ''"
              @click="toggleStandard(std.id)"
            >
              <input
                type="checkbox"
                tabindex="-1"
                :checked="form.standards.includes(std.id)"
                class="mt-1 pointer-events-none rounded border-gray-300 text-primary-600"
              />
              <span class="flex-grow">
                <span class="font-medium text-gray-900">{{ std.code }}</span>
                <span class="text-gray-600"> — {{ std.description }}</span>
                <span class="block text-xs text-gray-400">{{ std.subject }}<template v-if="std.grade_level"> · {{ std.grade_level }}</template></span>
              </span>
            </button>
            <div v-if="!filteredStandards.length" class="px-3 py-3 text-xs text-gray-400 text-center">
              {{ t('lessonPlans.standardsPicker.noMatch') }}
            </div>
          </div>
        </div>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('lessonPlans.fields.status') }}</label>
            <!-- status is read-only; it changes via the submit/publish/archive buttons below -->
            <div class="w-full px-3 py-2 border border-gray-200 rounded-lg bg-gray-50 text-gray-700">
              {{ t(`lessonPlans.status.${form.status}`) }}
            </div>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('lessonPlans.fields.visibility') }}</label>
            <select v-model="form.visibility" class="w-full px-3 py-2 border border-gray-300 rounded-lg">
              <option v-for="v in ['private','unlisted','public']" :key="v" :value="v">{{ t(`lessonPlans.visibility.${v}`) }}</option>
            </select>
          </div>
        </div>

        <!-- state-machine + export actions -->
        <div v-if="!isNew" class="flex flex-wrap gap-2 pt-2 border-t border-gray-100">
          <AppButton size="sm" variant="secondary" :loading="acting" @click="transition('submit')">{{ t('lessonPlans.actions.submit') }}</AppButton>
          <AppButton size="sm" variant="secondary" :loading="acting" @click="transition('publish')">{{ t('lessonPlans.actions.publish') }}</AppButton>
          <AppButton size="sm" variant="ghost" :loading="acting" @click="transition('archive')">{{ t('lessonPlans.actions.archive') }}</AppButton>
          <AppButton
            size="sm"
            variant="ghost"
            class="ml-auto"
            @click="router.push({ name: 'lesson-plan-class', params: { id: planId as string } })"
          >
            {{ t('lessonPlans.classMode.open') }}
          </AppButton>
          <AppButton size="sm" variant="ghost" :loading="exportingPdf" @click="exportPdf">{{ t('lessonPlans.actions.exportPdf') }}</AppButton>
          <AppButton size="sm" variant="ghost" :loading="exporting" @click="exportScorm">{{ t('lessonPlans.actions.exportScorm') }}</AppButton>
        </div>
      </section>

      <!-- Activities (reorderable) -->
      <section class="space-y-3">
        <div class="flex items-center justify-between">
          <h2 class="text-xl font-semibold text-gray-900">{{ t('lessonPlans.activities') }}</h2>
          <AppButton size="sm" variant="secondary" @click="addActivity">{{ t('lessonPlans.addActivity') }}</AppButton>
        </div>
        <p class="text-sm text-gray-500">{{ t('lessonPlans.reorderHint') }}</p>

        <div
          v-for="(activity, index) in form.activities"
          :key="activity.id || index"
          class="bg-white rounded-lg shadow-sm p-4 border border-gray-100"
          draggable="true"
          @dragstart="onDragStart(index)"
          @dragover.prevent
          @drop="onDrop(index)"
        >
          <div class="flex items-start gap-3">
            <div class="mt-2 cursor-move text-gray-400 select-none" :title="t('lessonPlans.dragToReorder')">⠿</div>
            <div class="flex-grow space-y-3">
              <div class="grid grid-cols-1 md:grid-cols-3 gap-3">
                <div class="md:col-span-2">
                  <AppInput v-model="activity.title" :placeholder="t('lessonPlans.fields.activityTitle')" />
                </div>
                <select v-model="activity.activity_type" class="px-3 py-2 border border-gray-300 rounded-lg">
                  <option v-for="type in ACTIVITY_TYPES" :key="type" :value="type">{{ t(`lessonPlans.activityTypes.${type}`) }}</option>
                </select>
              </div>
              <textarea v-model="activity.instructions" rows="2" class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent" :placeholder="t('lessonPlans.fields.instructions')"></textarea>

              <!-- content picker: bind a real heritage item / route / resource / quiz -->
              <ActivityContentPicker
                :heritage-item="activity.heritage_item"
                :route="activity.route"
                :educational-resource="activity.educational_resource"
                :lom-general="activity.lom_general"
                :heritage-item-title="activity.heritage_item_title"
                :route-title="activity.route_title"
                :educational-resource-title="activity.educational_resource_title"
                :lom-general-title="activity.lom_general_title"
                @change="(p) => onBindingChange(index, p)"
              />

              <!-- quiz authoring for assess activities: edit the bound quiz (A.5)
                   directly, or resolve it from the bound heritage item -->
              <div v-if="activity.activity_type === 'assess'" class="border-t border-gray-100 pt-3">
                <template v-if="activity.lom_general">
                  <QuizEditor :lom-general-id="String(activity.lom_general)" />
                </template>
                <template v-else-if="!activity.heritage_item">
                  <p class="text-xs text-gray-500">{{ t('quiz.needHeritage') }}</p>
                </template>
                <template v-else-if="activity._quizLomId">
                  <QuizEditor :lom-general-id="activity._quizLomId" />
                </template>
                <template v-else>
                  <button
                    type="button"
                    class="text-sm text-primary-600 hover:underline disabled:opacity-50"
                    :disabled="activity._quizResolving"
                    @click="openQuiz(activity)"
                  >
                    {{ activity._quizResolving ? t('common.loading') : t('quiz.editQuiz') }}
                  </button>
                  <span v-if="activity._quizError && !activity._quizResolving" class="ml-2 text-xs text-red-600">{{ activity._quizError }}</span>
                </template>
              </div>

              <div class="flex items-center gap-3">
                <input v-model.number="activity.duration_minutes" type="number" min="0" class="w-28 px-3 py-1.5 border border-gray-300 rounded-lg" :placeholder="t('lessonPlans.fields.minutes')" />
                <span class="text-xs text-gray-400">{{ t('lessonPlans.fields.minutes') }}</span>
                <button type="button" class="ml-auto text-sm text-red-600 hover:underline" @click="removeActivity(index)">
                  {{ t('common.delete') }}
                </button>
              </div>
            </div>
          </div>
        </div>

        <div v-if="form.activities.length === 0" class="text-center text-gray-500 py-8 border border-dashed border-gray-200 rounded-lg">
          {{ t('lessonPlans.noActivities') }}
        </div>
      </section>
    </template>
  </div>
</template>
