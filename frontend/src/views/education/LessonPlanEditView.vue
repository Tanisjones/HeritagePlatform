<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { lessonPlanService } from '@/services/api'
import { useAsyncAction } from '@/composables/useAsyncAction'
import { useToast } from '@/composables/useDialogs'
import type { LessonActivity, LessonActivityType, LessonPlan, LessonPlanWriteData } from '@/types/heritage'
import AppButton from '@/components/common/AppButton.vue'
import AppInput from '@/components/common/AppInput.vue'
import ErrorBanner from '@/components/common/ErrorBanner.vue'
import BaseSpinner from '@/components/common/BaseSpinner.vue'

const route = useRoute()
const router = useRouter()
const { t } = useI18n()
const toast = useToast()
const { loading, error, run } = useAsyncAction()
const saving = ref(false)
const saveError = ref<string | null>(null)

const planId = computed(() => (route.params.id ? String(route.params.id) : null))
const isNew = computed(() => !planId.value)

const ACTIVITY_TYPES: LessonActivityType[] = ['hook', 'explore', 'explain', 'practice', 'assess', 'reflect']

// The editable form. `objectivesText` is a textarea buffer (one objective per line).
const form = reactive<{
  title: string
  summary: string
  subject: string
  grade_level: string
  status: LessonPlan['status']
  visibility: LessonPlan['visibility']
  objectivesText: string
  activities: LessonActivity[]
}>({
  title: '',
  summary: '',
  subject: '',
  grade_level: '',
  status: 'draft',
  visibility: 'private',
  objectivesText: '',
  activities: [],
})

function hydrate(plan: LessonPlan) {
  form.title = plan.title
  form.summary = plan.summary || ''
  form.subject = plan.subject || ''
  form.grade_level = plan.grade_level || ''
  form.status = plan.status
  form.visibility = plan.visibility
  form.objectivesText = (plan.objectives || []).join('\n')
  form.activities = (plan.activities || [])
    .slice()
    .sort((a, b) => a.order - b.order)
    .map((a) => ({ ...a }))
}

async function load() {
  if (isNew.value) {
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
  })
}

function removeActivity(index: number) {
  form.activities.splice(index, 1)
  reindex()
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
    status: form.status,
    visibility: form.visibility,
    objectives,
    // Send only the fields the write serializer accepts; keep `id` so existing
    // activities reconcile by identity (preserving their UUIDs on reorder).
    activities: form.activities.map((a, i) => ({
      ...(a.id ? { id: a.id } : {}),
      order: i,
      title: a.title,
      activity_type: a.activity_type,
      instructions: a.instructions || '',
      duration_minutes: a.duration_minutes ?? null,
      materials: a.materials || '',
    })),
  }
}

async function save() {
  if (!canSave.value) return
  saving.value = true
  saveError.value = null
  try {
    const payload = buildPayload()
    const res = isNew.value
      ? await lessonPlanService.create(payload)
      : await lessonPlanService.update(planId.value as string, payload)
    toast.success(t('common.saved'))
    router.replace({ name: 'lesson-plan-edit', params: { id: (res.data as LessonPlan).id } })
    hydrate(res.data as LessonPlan)
  } catch (e: any) {
    saveError.value = e?.response?.data ? JSON.stringify(e.response.data) : t('common.errorSaving')
  } finally {
    saving.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="max-w-4xl mx-auto p-5 space-y-6">
    <div class="flex items-center justify-between gap-4">
      <h1 class="text-3xl font-display font-bold text-gray-900">
        {{ isNew ? t('lessonPlans.newTitle') : t('lessonPlans.editTitle') }}
      </h1>
      <div class="flex gap-2">
        <AppButton variant="ghost" @click="router.push({ name: 'lesson-plans' })">
          {{ t('common.cancel') }}
        </AppButton>
        <AppButton :loading="saving" :disabled="!canSave" @click="save">{{ t('common.save') }}</AppButton>
      </div>
    </div>

    <ErrorBanner :message="error" @retry="load" />
    <ErrorBanner :message="saveError" :retryable="false" dense />

    <div v-if="loading" class="flex justify-center py-16">
      <BaseSpinner class="h-8 w-8 text-primary-600" />
    </div>

    <template v-else>
      <!-- Plan header -->
      <section class="bg-white rounded-lg shadow-sm p-5 space-y-4">
        <AppInput v-model="form.title" :label="t('lessonPlans.fields.title')" :placeholder="t('lessonPlans.fields.titlePlaceholder')" />
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('lessonPlans.fields.summary') }}</label>
          <textarea v-model="form.summary" rows="2" class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"></textarea>
        </div>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <AppInput v-model="form.subject" :label="t('lessonPlans.fields.subject')" />
          <AppInput v-model="form.grade_level" :label="t('lessonPlans.fields.gradeLevel')" />
        </div>
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('lessonPlans.fields.objectives') }}</label>
          <textarea v-model="form.objectivesText" rows="3" class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent" :placeholder="t('lessonPlans.fields.objectivesPlaceholder')"></textarea>
          <p class="mt-1 text-xs text-gray-500">{{ t('lessonPlans.fields.objectivesHelp') }}</p>
        </div>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('lessonPlans.fields.status') }}</label>
            <select v-model="form.status" class="w-full px-3 py-2 border border-gray-300 rounded-lg">
              <option v-for="s in ['draft','review','published','archived']" :key="s" :value="s">{{ t(`lessonPlans.status.${s}`) }}</option>
            </select>
          </div>
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('lessonPlans.fields.visibility') }}</label>
            <select v-model="form.visibility" class="w-full px-3 py-2 border border-gray-300 rounded-lg">
              <option v-for="v in ['private','unlisted','public']" :key="v" :value="v">{{ t(`lessonPlans.visibility.${v}`) }}</option>
            </select>
          </div>
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
