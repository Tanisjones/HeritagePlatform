<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import {
  LOM_RESOURCE_TYPES, LOM_DIFFICULTIES, LOM_CONTEXTS, LOM_INTERACTIVITY_TYPES,
  LOM_END_USER_ROLES, LOM_PEDAGOGICAL_APPROACHES,
} from '@/constants/lomVocab'
import { useDurationValidation } from '@/composables/useDurationValidation'
import AiActionButton from '@/components/common/AiActionButton.vue'

/**
 * Step 5 of the contribution wizard: the IEEE-LOM §5 educational layer.
 * Extracted from ContributionForm's god-template. The parent owns the
 * `educational` reactive draft (passed in and mutated in place via v-model on
 * its fields) and the objectives text buffer; AI generation stays in the parent
 * (it needs the contribution's title/description), surfaced here via `aiLoading`
 * / `aiError` / `aiNote` and the `generate` event.
 */
export interface EducationalDraft {
  learning_resource_type: string
  difficulty: string
  typical_age_range: string
  typical_learning_time: string
  context: string
  interactivity_type: string
  intended_end_user_role: string
  pedagogical_approach: string
  learning_objectives: string[]
  prerequisites: string
  competencies: string
}

const props = defineProps<{
  educational: EducationalDraft
  objectivesText: string
  aiAvailable: boolean
  aiLoading: boolean
  aiError: string
  aiNote: string
  submitting: boolean
}>()

const emit = defineEmits<{
  'update:objectivesText': [value: string]
  /** Objectives textarea lost focus — parent should sync the list from the text. */
  syncObjectives: []
  /** "Generate with AI" pressed. */
  generate: []
}>()

const { t } = useI18n()

// Same ISO-8601 guard the parent used, recomputed from the shared draft.
const eduTimeError = useDurationValidation(
  () => props.educational.typical_learning_time,
  { invalidKey: 'contribution.step5edu.errors.duration', monthsKey: 'contribution.step5edu.errors.months' },
)

const resourceTypeOptions = LOM_RESOURCE_TYPES
const difficultyOptions = LOM_DIFFICULTIES
const contextOptions = LOM_CONTEXTS
const interactivityOptions = LOM_INTERACTIVITY_TYPES
const endUserRoleOptions = LOM_END_USER_ROLES
const pedagogicalApproachOptions = LOM_PEDAGOGICAL_APPROACHES

const objectives = computed({
  get: () => props.objectivesText,
  set: (v: string) => emit('update:objectivesText', v),
})
</script>

<template>
  <div class="space-y-6">
    <div class="bg-primary-50 p-4 rounded-lg text-primary-800 text-sm">
      {{ t('contribution.step5edu.instruction') }}
    </div>

    <AiActionButton
      :label="t('ai.educationalButton')"
      :loading-label="t('ai.educationalGenerating')"
      :loading="aiLoading"
      :available="aiAvailable"
      :disabled="submitting"
      :error="aiError"
      @click="emit('generate')"
    />

    <p v-if="aiNote" class="text-sm text-emerald-700 bg-emerald-50 border border-emerald-200 px-3 py-2 rounded-lg">
      {{ aiNote }}
    </p>

    <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
      <div>
        <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('contribution.step5edu.fields.resourceType') }}</label>
        <select v-model="educational.learning_resource_type" class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-primary-500 focus:border-primary-500">
          <option value="">{{ t('contribution.step5edu.unset') }}</option>
          <option v-for="opt in resourceTypeOptions" :key="opt" :value="opt">{{ t(`lom.resource_type.${opt}`, opt) }}</option>
        </select>
      </div>
      <div>
        <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('contribution.step5edu.fields.difficulty') }}</label>
        <select v-model="educational.difficulty" class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-primary-500 focus:border-primary-500">
          <option value="">{{ t('contribution.step5edu.unset') }}</option>
          <option v-for="opt in difficultyOptions" :key="opt" :value="opt">{{ t(`lom.difficulty.${opt}`, opt) }}</option>
        </select>
      </div>
      <div>
        <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('contribution.step5edu.fields.context') }}</label>
        <select v-model="educational.context" class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-primary-500 focus:border-primary-500">
          <option value="">{{ t('contribution.step5edu.unset') }}</option>
          <option v-for="opt in contextOptions" :key="opt" :value="opt">{{ t(`lom.context.${opt}`, opt) }}</option>
        </select>
      </div>
      <div>
        <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('contribution.step5edu.fields.ageRange') }}</label>
        <input v-model="educational.typical_age_range" type="text" class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-primary-500 focus:border-primary-500" :placeholder="t('contribution.step5edu.placeholders.ageRange')" />
      </div>
      <div>
        <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('contribution.step5edu.fields.learningTime') }}</label>
        <input v-model="educational.typical_learning_time" type="text" class="w-full px-4 py-2 border rounded-lg focus:ring-primary-500 focus:border-primary-500" :class="eduTimeError ? 'border-red-400' : 'border-gray-300'" :placeholder="t('contribution.step5edu.placeholders.learningTime')" />
        <p v-if="eduTimeError" class="text-xs text-red-600 mt-1">{{ eduTimeError }}</p>
        <p v-else class="text-xs text-gray-500 mt-1">{{ t('contribution.step5edu.help.learningTime') }}</p>
      </div>
      <div>
        <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('contribution.step5edu.fields.interactivity') }}</label>
        <select v-model="educational.interactivity_type" class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-primary-500 focus:border-primary-500">
          <option value="">{{ t('contribution.step5edu.unset') }}</option>
          <option v-for="opt in interactivityOptions" :key="opt" :value="opt">{{ t(`lom.interactivity.${opt}`, opt) }}</option>
        </select>
      </div>
      <div>
        <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('contribution.step5edu.fields.audience') }}</label>
        <select v-model="educational.intended_end_user_role" class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-primary-500 focus:border-primary-500">
          <option value="">{{ t('contribution.step5edu.unset') }}</option>
          <option v-for="opt in endUserRoleOptions" :key="opt" :value="opt">{{ t(`lom.audience.${opt}`, opt) }}</option>
        </select>
      </div>
      <div>
        <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('contribution.step5edu.fields.approach') }}</label>
        <select v-model="educational.pedagogical_approach" class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-primary-500 focus:border-primary-500">
          <option value="">{{ t('contribution.step5edu.unset') }}</option>
          <option v-for="opt in pedagogicalApproachOptions" :key="opt" :value="opt">{{ t(`lom.approach.${opt}`, opt) }}</option>
        </select>
      </div>
    </div>

    <div>
      <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('contribution.step5edu.fields.objectives') }}</label>
      <textarea v-model="objectives" @blur="emit('syncObjectives')" rows="4" class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-primary-500 focus:border-primary-500" :placeholder="t('contribution.step5edu.placeholders.objectives')"></textarea>
      <p class="text-xs text-gray-500 mt-1">{{ t('contribution.step5edu.help.objectives') }}</p>
    </div>

    <div>
      <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('contribution.step5edu.fields.prerequisites') }}</label>
      <textarea v-model="educational.prerequisites" rows="2" class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-primary-500 focus:border-primary-500" :placeholder="t('contribution.step5edu.placeholders.prerequisites')"></textarea>
    </div>

    <div>
      <label class="block text-sm font-medium text-gray-700 mb-1">{{ t('contribution.step5edu.fields.competencies') }}</label>
      <textarea v-model="educational.competencies" rows="2" class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-primary-500 focus:border-primary-500" :placeholder="t('contribution.step5edu.placeholders.competencies')"></textarea>
    </div>
  </div>
</template>
