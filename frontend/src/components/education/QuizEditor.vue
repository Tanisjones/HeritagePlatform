<script setup lang="ts">
/**
 * P.5 — author a learning object's quiz (AssessmentQuestion CRUD).
 *
 * Bound to a LOMGeneral id: loads its questions, lets the teacher add/edit/remove/
 * reorder questions of the four types (single/multiple choice, true-false,
 * short-answer) with an answer key + feedback, and saves them in ONE nested PATCH
 * /lom/{id}/ (LOMGeneralWriteSerializer.questions reconciles by id). Choice ids are
 * stable slugs the backend keeps; `correct` lives on each choice for choice types,
 * `correct_response` for short-answer / true-false.
 */
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { educationService } from '@/services/api'
import { withLoading } from '@/composables/useAsyncAction'
import { useToast } from '@/composables/useDialogs'
import type { AssessmentQuestion } from '@/types/heritage'
import AppButton from '@/components/common/AppButton.vue'
import ErrorBanner from '@/components/common/ErrorBanner.vue'
import BaseSpinner from '@/components/common/BaseSpinner.vue'

const props = defineProps<{ lomGeneralId: string }>()
const { t } = useI18n()
const toast = useToast()

const loading = ref(false)
const error = ref<string | null>(null)
const saving = ref(false)
const saveError = ref<string | null>(null)

const QUESTION_TYPES = ['single_choice', 'multiple_choice', 'true_false', 'short_answer'] as const
type QuestionType = (typeof QUESTION_TYPES)[number]

const questions = ref<AssessmentQuestion[]>([])

async function load() {
  await withLoading(loading, error, async () => {
    const res = await educationService.getLom(props.lomGeneralId)
    const list = (res.data?.questions || []) as AssessmentQuestion[]
    questions.value = list
      .slice()
      .sort((a, b) => (a.order ?? 0) - (b.order ?? 0))
      .map((q) => ({ ...q, choices: (q.choices || []).map((c) => ({ ...c })) }))
  })
}

let choiceSeq = 0
function newChoiceId(): string {
  choiceSeq += 1
  return `c${choiceSeq}_${questions.value.length}`
}

function addQuestion() {
  questions.value.push({
    order: questions.value.length,
    question_type: 'single_choice',
    prompt: '',
    choices: [
      { id: newChoiceId(), text: '', correct: true },
      { id: newChoiceId(), text: '', correct: false },
    ],
    correct_response: '',
    feedback: '',
  })
}

function removeQuestion(index: number) {
  questions.value.splice(index, 1)
  reindex()
}

function reindex() {
  questions.value.forEach((q, i) => (q.order = i))
}

function addChoice(q: AssessmentQuestion) {
  ;(q.choices ||= []).push({ id: newChoiceId(), text: '', correct: false })
}
function removeChoice(q: AssessmentQuestion, ci: number) {
  q.choices?.splice(ci, 1)
}

/** Single-choice: selecting one correct answer clears the others. */
function setSingleCorrect(q: AssessmentQuestion, ci: number) {
  q.choices?.forEach((c, i) => (c.correct = i === ci))
}

function onTypeChange(q: AssessmentQuestion) {
  if (q.question_type === 'true_false') {
    q.choices = []
    if (q.correct_response !== 'true' && q.correct_response !== 'false') q.correct_response = 'true'
  } else if (q.question_type === 'short_answer') {
    q.choices = []
  } else {
    // choice types: ensure at least two options exist
    if (!q.choices || q.choices.length < 2) {
      q.choices = [
        { id: newChoiceId(), text: '', correct: true },
        { id: newChoiceId(), text: '', correct: false },
      ]
    }
  }
}

function isChoice(type?: QuestionType): boolean {
  return type === 'single_choice' || type === 'multiple_choice'
}

async function save() {
  saving.value = true
  saveError.value = null
  try {
    // Send only the fields the nested write serializer accepts; keep `id` so
    // existing questions reconcile by identity (preserving UUIDs on reorder).
    const payload = {
      questions: questions.value.map((q, i) => ({
        ...(q.id ? { id: q.id } : {}),
        order: i,
        question_type: q.question_type,
        prompt: q.prompt || '',
        choices: isChoice(q.question_type as QuestionType)
          ? (q.choices || []).map((c) => ({ id: c.id, text: c.text || '', correct: !!c.correct }))
          : [],
        correct_response: q.question_type === 'short_answer' || q.question_type === 'true_false'
          ? q.correct_response || ''
          : '',
        feedback: q.feedback || '',
      })),
    }
    const res = await educationService.updateLom(props.lomGeneralId, payload)
    const list = (res.data?.questions || []) as AssessmentQuestion[]
    questions.value = list
      .slice()
      .sort((a, b) => (a.order ?? 0) - (b.order ?? 0))
      .map((q) => ({ ...q, choices: (q.choices || []).map((c) => ({ ...c })) }))
    toast.success(t('common.saved'))
  } catch (e: any) {
    saveError.value = e?.response?.data ? JSON.stringify(e.response.data) : t('common.errorSaving')
  } finally {
    saving.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="space-y-4">
    <div class="flex items-center justify-between">
      <h3 class="text-lg font-semibold text-gray-900">{{ t('quiz.title') }}</h3>
      <div class="flex gap-2">
        <AppButton size="sm" variant="secondary" @click="addQuestion">{{ t('quiz.addQuestion') }}</AppButton>
        <AppButton size="sm" :loading="saving" @click="save">{{ t('common.save') }}</AppButton>
      </div>
    </div>

    <ErrorBanner :message="error" @retry="load" />
    <ErrorBanner :message="saveError" :retryable="false" dense />

    <div v-if="loading" class="flex justify-center py-8"><BaseSpinner class="h-6 w-6 text-primary-600" /></div>

    <template v-else>
      <div
        v-for="(q, index) in questions"
        :key="q.id || index"
        class="bg-white border border-gray-200 rounded-lg p-4 space-y-3"
      >
        <div class="flex items-center gap-3">
          <span class="text-sm text-gray-400">#{{ index + 1 }}</span>
          <select
            v-model="q.question_type"
            class="px-3 py-1.5 border border-gray-300 rounded-lg text-sm"
            @change="onTypeChange(q)"
          >
            <option v-for="type in QUESTION_TYPES" :key="type" :value="type">{{ t(`quiz.types.${type}`) }}</option>
          </select>
          <button type="button" class="ml-auto text-sm text-red-600 hover:underline" @click="removeQuestion(index)">
            {{ t('common.delete') }}
          </button>
        </div>

        <textarea
          v-model="q.prompt"
          rows="2"
          class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500"
          :placeholder="t('quiz.promptPlaceholder')"
        ></textarea>

        <!-- choice types -->
        <div v-if="isChoice(q.question_type)" class="space-y-2">
          <div v-for="(choice, ci) in q.choices" :key="choice.id || ci" class="flex items-center gap-2">
            <input
              v-if="q.question_type === 'single_choice'"
              type="radio"
              :checked="choice.correct"
              @change="setSingleCorrect(q, ci)"
            />
            <input v-else type="checkbox" v-model="choice.correct" />
            <input
              v-model="choice.text"
              type="text"
              class="flex-grow px-3 py-1.5 border border-gray-300 rounded-lg text-sm"
              :placeholder="t('quiz.optionPlaceholder')"
            />
            <button type="button" class="text-gray-400 hover:text-red-600" @click="removeChoice(q, ci)">✕</button>
          </div>
          <button type="button" class="text-sm text-primary-600 hover:underline" @click="addChoice(q)">
            + {{ t('quiz.addOption') }}
          </button>
        </div>

        <!-- true / false -->
        <div v-else-if="q.question_type === 'true_false'" class="flex items-center gap-4 text-sm">
          <span class="text-gray-600">{{ t('quiz.correctAnswer') }}:</span>
          <label class="flex items-center gap-1">
            <input type="radio" value="true" v-model="q.correct_response" /> {{ t('quiz.true') }}
          </label>
          <label class="flex items-center gap-1">
            <input type="radio" value="false" v-model="q.correct_response" /> {{ t('quiz.false') }}
          </label>
        </div>

        <!-- short answer -->
        <div v-else-if="q.question_type === 'short_answer'">
          <input
            v-model="q.correct_response"
            type="text"
            class="w-full px-3 py-1.5 border border-gray-300 rounded-lg text-sm"
            :placeholder="t('quiz.expectedAnswer')"
          />
        </div>

        <input
          v-model="q.feedback"
          type="text"
          class="w-full px-3 py-1.5 border border-gray-200 rounded-lg text-sm text-gray-600"
          :placeholder="t('quiz.feedbackPlaceholder')"
        />
      </div>

      <div v-if="questions.length === 0" class="text-center text-gray-500 py-6 border border-dashed border-gray-200 rounded-lg">
        {{ t('quiz.empty') }}
      </div>
    </template>
  </div>
</template>
