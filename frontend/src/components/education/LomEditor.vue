<script setup lang="ts">
/**
 * LomEditor.vue
 *
 * Full authoring UI for the IEEE-LOM educational layer of a heritage item.
 * Edits the general + nested educational / rights / lifecycle / classifications
 * in a single PATCH /lom/{id}/ against the backend nested write serializer
 * (LOMGeneralWriteSerializer). Includes an AI-assist button that fills the
 * educational fields from the item's title/description.
 *
 * Intended for curators / teachers (the parent view gates visibility).
 */
import { reactive, ref, watch } from 'vue';
import type { LOMMetadata, LOMEducational, LOMClassification } from '@/types/heritage';
import { educationService, aiService } from '@/services/api';
import { useAIAvailability } from '@/services/aiAvailability';
import { useAiError } from '@/composables/useAiError';
import { isValidIso8601Duration, looksLikeMonthsNotMinutes } from '@/utils/duration';
import {
  LOM_RESOURCE_TYPES, LOM_DIFFICULTIES, LOM_CONTEXTS, LOM_INTERACTIVITY_TYPES,
  LOM_INTERACTIVITY_LEVELS, LOM_END_USER_ROLES, LOM_PEDAGOGICAL_APPROACHES,
  LOM_LIFECYCLE_STATUSES, LOM_CLASSIFICATION_PURPOSES,
} from '@/constants/lomVocab';
import AiActionButton from '@/components/common/AiActionButton.vue';
import AppButton from '@/components/common/AppButton.vue';
import BaseSpinner from '@/components/common/BaseSpinner.vue';
import { useI18n } from 'vue-i18n';

const props = defineProps<{
  lomId: string;
  metadata?: LOMMetadata | null;
  language?: string;
}>();

const emit = defineEmits<{ (e: 'saved', metadata: any): void; (e: 'cancel'): void }>();

const { t, locale } = useI18n();
const { isAvailable: aiAvailable, refresh: refreshAI } = useAIAvailability();
const { applyAIError } = useAiError();

// --- Vocabularies (shared with the wizard and /learn; mirror backend choices) ---
const resourceTypeOptions = LOM_RESOURCE_TYPES;
const difficultyOptions = LOM_DIFFICULTIES;
const contextOptions = LOM_CONTEXTS;
const interactivityOptions = LOM_INTERACTIVITY_TYPES;
const interactivityLevelOptions = LOM_INTERACTIVITY_LEVELS;
const endUserRoleOptions = LOM_END_USER_ROLES;
const pedagogicalApproachOptions = LOM_PEDAGOGICAL_APPROACHES;
const lifecycleStatusOptions = LOM_LIFECYCLE_STATUSES;
const classificationPurposeOptions = LOM_CLASSIFICATION_PURPOSES;

// --- Editable form state ---
const general = reactive({
  coverage: '',
  structure: 'atomic',
  aggregation_level: 1,
});
const educational = reactive<Record<string, any>>({
  learning_resource_type: 'narrative_text',
  interactivity_type: 'expositive',
  interactivity_level: 'medium',
  intended_end_user_role: 'learner',
  context: 'other',
  difficulty: 'medium',
  typical_age_range: '',
  typical_learning_time: '',
  description: '',
  pedagogical_approach: '',
  curriculum_alignment: '',
  prerequisites: '',
  competencies: '',
  suggested_activities: '',
  learning_objectives: [] as string[],
});
const objectivesText = ref('');
const rights = reactive({
  cost: false,
  copyright_and_other_restrictions: true,
  description: '',
});
const lifecycle = reactive({
  version: '',
  status: 'draft',
});
const classifications = ref<LOMClassification[]>([]);

const saving = ref(false);
const saveError = ref<string | null>(null);
const saveOk = ref(false);
const aiLoading = ref(false);
const aiError = ref('');
const aiNote = ref('');

// ISO-8601 duration client-side guard (shared with /learn; mirrors the backend
// validator). Also warns on the "P30M means 30 months, not minutes" footgun.
const learningTimeError = ref('');
watch(() => educational.typical_learning_time, (value) => {
  if (value && !isValidIso8601Duration(value)) {
    learningTimeError.value = t('lomEditor.errors.duration');
  } else if (looksLikeMonthsNotMinutes(value)) {
    learningTimeError.value = t('lomEditor.errors.months');
  } else {
    learningTimeError.value = '';
  }
});

// --- Hydrate from the current metadata ---
const firstEducational = (m?: LOMMetadata | null): LOMEducational | undefined => {
  const edu = m?.educational;
  if (!edu) return undefined;
  return Array.isArray(edu) ? edu[0] : edu;
};

const hydrate = () => {
  const m = props.metadata;
  general.coverage = m?.coverage ?? '';
  general.structure = m?.structure ?? 'atomic';
  general.aggregation_level = m?.aggregation_level ?? 1;

  const edu = firstEducational(m);
  if (edu) {
    Object.keys(educational).forEach((k) => {
      if (k === 'learning_objectives') return;
      if ((edu as any)[k] !== undefined && (edu as any)[k] !== null) educational[k] = (edu as any)[k];
    });
    educational.learning_objectives = Array.isArray(edu.learning_objectives) ? [...edu.learning_objectives] : [];
    objectivesText.value = educational.learning_objectives.join('\n');
  }

  if (m?.rights) {
    rights.cost = !!m.rights.cost;
    rights.copyright_and_other_restrictions = m.rights.copyright_and_other_restrictions !== false;
    rights.description = m.rights.description ?? '';
  }
  if (m?.lifecycle) {
    lifecycle.version = m.lifecycle.version ?? '';
    lifecycle.status = m.lifecycle.status ?? 'draft';
  }
  classifications.value = Array.isArray(m?.classifications)
    ? m!.classifications!.map((c) => ({ ...c }))
    : [];
};

watch(() => props.metadata, hydrate, { immediate: true });
refreshAI();

const syncObjectives = () => {
  educational.learning_objectives = objectivesText.value
    .split('\n')
    .map((s) => s.trim())
    .filter(Boolean);
};

const addClassification = () => {
  classifications.value.push({ purpose: 'discipline', taxon_source: '', taxon_entry: '' });
};
const removeClassification = (idx: number) => {
  classifications.value.splice(idx, 1);
};

const generateWithAI = async () => {
  if (aiLoading.value || saving.value) return;
  aiError.value = '';
  aiNote.value = '';
  try {
    aiLoading.value = true;
    const res = await aiService.educationalMetadata({
      language: String(props.language || locale.value || 'es'),
      title: String(props.metadata?.title || ''),
      description: String(props.metadata?.description || ''),
      resource_type: educational.learning_resource_type || '',
    });
    const applyEnum = (key: string, value: string | null | undefined, allowed: readonly string[]) => {
      if (value && allowed.includes(value)) educational[key] = value;
    };
    applyEnum('learning_resource_type', res.learning_resource_type, resourceTypeOptions);
    applyEnum('difficulty', res.difficulty, difficultyOptions);
    applyEnum('context', res.context, contextOptions);
    if (res.typical_age_range) educational.typical_age_range = res.typical_age_range;
    if (res.typical_learning_time) educational.typical_learning_time = res.typical_learning_time;
    if (Array.isArray(res.learning_objectives) && res.learning_objectives.length) {
      educational.learning_objectives = res.learning_objectives;
      objectivesText.value = res.learning_objectives.join('\n');
    }
    aiNote.value = t('ai.educationalApplied');
  } catch (err: any) {
    applyAIError(err, aiError);
  } finally {
    aiLoading.value = false;
  }
};

const save = async () => {
  if (saving.value) return;
  syncObjectives();
  if (learningTimeError.value) return;
  saveError.value = null;
  saveOk.value = false;

  // Classifications are sent as a full replace-all set, so we must send EVERY
  // current row (dropping incomplete ones would let the backend delete them).
  // A row missing its required taxon fields would fail backend validation, so
  // block the save and tell the user rather than silently discarding data.
  const incomplete = classifications.value.some(
    (c) => !(c.purpose && c.taxon_source && c.taxon_entry)
  );
  if (incomplete) {
    saveError.value = t('lomEditor.errors.incompleteClassification');
    return;
  }
  const allClassifications = classifications.value.map((c) => ({
    purpose: c.purpose,
    taxon_source: c.taxon_source,
    taxon_id: c.taxon_id || '',
    taxon_entry: c.taxon_entry,
    description: c.description || '',
    keywords: c.keywords || '',
  }));

  // Coerce aggregation_level: a cleared number input yields '' / NaN, which the
  // backend IntegerField would 400 on — fall back to 1.
  const aggregationLevel = Number.isFinite(general.aggregation_level)
    ? general.aggregation_level
    : 1;

  const payload = {
    coverage: general.coverage,
    structure: general.structure,
    aggregation_level: aggregationLevel,
    educational: { ...educational },
    rights: { ...rights },
    lifecycle: { ...lifecycle },
    classifications: allClassifications,
  };

  try {
    saving.value = true;
    const res = await educationService.updateLom(props.lomId, payload);
    saveOk.value = true;
    emit('saved', res.data);
  } catch (e: any) {
    saveError.value = e?.response?.data ? JSON.stringify(e.response.data) : String(e);
  } finally {
    saving.value = false;
  }
};
</script>

<template>
  <div class="space-y-8">
    <div class="flex items-center justify-between">
      <h3 class="font-display text-xl font-bold text-gray-900">{{ t('lomEditor.title') }}</h3>
      <AiActionButton
        :label="t('ai.educationalButton')"
        :loading-label="t('ai.educationalGenerating')"
        :loading="aiLoading"
        :available="aiAvailable"
        :disabled="saving"
        :error="aiError"
        @click="generateWithAI"
      />
    </div>
    <p v-if="aiNote" class="text-sm text-emerald-700 bg-emerald-50 border border-emerald-200 px-3 py-2 rounded-lg">{{ aiNote }}</p>

    <!-- Educational (§5) -->
    <section class="space-y-4">
      <h4 class="text-sm font-bold text-secondary-700 uppercase tracking-wider">{{ t('lomEditor.sections.educational') }}</h4>
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <label class="block">
          <span class="text-sm font-medium text-gray-700">{{ t('contribution.step5edu.fields.resourceType') }}</span>
          <select v-model="educational.learning_resource_type" class="mt-1 w-full px-3 py-2 border border-gray-300 rounded-lg">
            <option v-for="o in resourceTypeOptions" :key="o" :value="o">{{ t(`lom.resource_type.${o}`, o) }}</option>
          </select>
        </label>
        <label class="block">
          <span class="text-sm font-medium text-gray-700">{{ t('contribution.step5edu.fields.difficulty') }}</span>
          <select v-model="educational.difficulty" class="mt-1 w-full px-3 py-2 border border-gray-300 rounded-lg">
            <option v-for="o in difficultyOptions" :key="o" :value="o">{{ t(`lom.difficulty.${o}`, o) }}</option>
          </select>
        </label>
        <label class="block">
          <span class="text-sm font-medium text-gray-700">{{ t('contribution.step5edu.fields.context') }}</span>
          <select v-model="educational.context" class="mt-1 w-full px-3 py-2 border border-gray-300 rounded-lg">
            <option v-for="o in contextOptions" :key="o" :value="o">{{ t(`lom.context.${o}`, o) }}</option>
          </select>
        </label>
        <label class="block">
          <span class="text-sm font-medium text-gray-700">{{ t('contribution.step5edu.fields.audience') }}</span>
          <select v-model="educational.intended_end_user_role" class="mt-1 w-full px-3 py-2 border border-gray-300 rounded-lg">
            <option v-for="o in endUserRoleOptions" :key="o" :value="o">{{ t(`lom.audience.${o}`, o) }}</option>
          </select>
        </label>
        <label class="block">
          <span class="text-sm font-medium text-gray-700">{{ t('contribution.step5edu.fields.interactivity') }}</span>
          <select v-model="educational.interactivity_type" class="mt-1 w-full px-3 py-2 border border-gray-300 rounded-lg">
            <option v-for="o in interactivityOptions" :key="o" :value="o">{{ t(`lom.interactivity.${o}`, o) }}</option>
          </select>
        </label>
        <label class="block">
          <span class="text-sm font-medium text-gray-700">{{ t('lomEditor.fields.interactivityLevel') }}</span>
          <select v-model="educational.interactivity_level" class="mt-1 w-full px-3 py-2 border border-gray-300 rounded-lg">
            <option v-for="o in interactivityLevelOptions" :key="o" :value="o">{{ t(`lom.level.${o}`, o) }}</option>
          </select>
        </label>
        <label class="block">
          <span class="text-sm font-medium text-gray-700">{{ t('contribution.step5edu.fields.ageRange') }}</span>
          <input v-model="educational.typical_age_range" type="text" class="mt-1 w-full px-3 py-2 border border-gray-300 rounded-lg" :placeholder="t('contribution.step5edu.placeholders.ageRange')" />
        </label>
        <label class="block">
          <span class="text-sm font-medium text-gray-700">{{ t('contribution.step5edu.fields.learningTime') }}</span>
          <input v-model="educational.typical_learning_time" type="text" class="mt-1 w-full px-3 py-2 border border-gray-300 rounded-lg" :placeholder="t('contribution.step5edu.placeholders.learningTime')" />
          <span v-if="learningTimeError" class="text-xs text-red-600">{{ learningTimeError }}</span>
          <span v-else class="text-xs text-gray-500">{{ t('contribution.step5edu.help.learningTime') }}</span>
        </label>
        <label class="block">
          <span class="text-sm font-medium text-gray-700">{{ t('contribution.step5edu.fields.approach') }}</span>
          <select v-model="educational.pedagogical_approach" class="mt-1 w-full px-3 py-2 border border-gray-300 rounded-lg">
            <option value="">{{ t('contribution.step5edu.unset') }}</option>
            <option v-for="o in pedagogicalApproachOptions" :key="o" :value="o">{{ t(`lom.approach.${o}`, o) }}</option>
          </select>
        </label>
        <label class="block">
          <span class="text-sm font-medium text-gray-700">{{ t('lomEditor.fields.curriculum') }}</span>
          <input v-model="educational.curriculum_alignment" type="text" class="mt-1 w-full px-3 py-2 border border-gray-300 rounded-lg" :placeholder="t('lomEditor.placeholders.curriculum')" />
        </label>
      </div>

      <label class="block">
        <span class="text-sm font-medium text-gray-700">{{ t('contribution.step5edu.fields.objectives') }}</span>
        <textarea v-model="objectivesText" @blur="syncObjectives" rows="3" class="mt-1 w-full px-3 py-2 border border-gray-300 rounded-lg" :placeholder="t('contribution.step5edu.placeholders.objectives')"></textarea>
        <span class="text-xs text-gray-500">{{ t('contribution.step5edu.help.objectives') }}</span>
      </label>
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <label class="block">
          <span class="text-sm font-medium text-gray-700">{{ t('contribution.step5edu.fields.prerequisites') }}</span>
          <textarea v-model="educational.prerequisites" rows="2" class="mt-1 w-full px-3 py-2 border border-gray-300 rounded-lg"></textarea>
        </label>
        <label class="block">
          <span class="text-sm font-medium text-gray-700">{{ t('contribution.step5edu.fields.competencies') }}</span>
          <textarea v-model="educational.competencies" rows="2" class="mt-1 w-full px-3 py-2 border border-gray-300 rounded-lg"></textarea>
        </label>
      </div>
      <label class="block">
        <span class="text-sm font-medium text-gray-700">{{ t('lomEditor.fields.activities') }}</span>
        <textarea v-model="educational.suggested_activities" rows="2" class="mt-1 w-full px-3 py-2 border border-gray-300 rounded-lg"></textarea>
      </label>
    </section>

    <!-- Rights -->
    <section class="space-y-4">
      <h4 class="text-sm font-bold text-secondary-700 uppercase tracking-wider">{{ t('lomEditor.sections.rights') }}</h4>
      <div class="flex flex-wrap gap-6">
        <label class="inline-flex items-center gap-2">
          <input v-model="rights.cost" type="checkbox" class="rounded border-gray-300" />
          <span class="text-sm text-gray-700">{{ t('lomEditor.fields.cost') }}</span>
        </label>
        <label class="inline-flex items-center gap-2">
          <input v-model="rights.copyright_and_other_restrictions" type="checkbox" class="rounded border-gray-300" />
          <span class="text-sm text-gray-700">{{ t('lomEditor.fields.copyright') }}</span>
        </label>
      </div>
      <label class="block">
        <span class="text-sm font-medium text-gray-700">{{ t('lomEditor.fields.rightsDescription') }}</span>
        <input v-model="rights.description" type="text" class="mt-1 w-full px-3 py-2 border border-gray-300 rounded-lg" :placeholder="t('lomEditor.placeholders.license')" />
      </label>
    </section>

    <!-- Lifecycle + General -->
    <section class="space-y-4">
      <h4 class="text-sm font-bold text-secondary-700 uppercase tracking-wider">{{ t('lomEditor.sections.lifecycle') }}</h4>
      <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
        <label class="block">
          <span class="text-sm font-medium text-gray-700">{{ t('lomEditor.fields.version') }}</span>
          <input v-model="lifecycle.version" type="text" class="mt-1 w-full px-3 py-2 border border-gray-300 rounded-lg" placeholder="1.0" />
        </label>
        <label class="block">
          <span class="text-sm font-medium text-gray-700">{{ t('lomEditor.fields.status') }}</span>
          <select v-model="lifecycle.status" class="mt-1 w-full px-3 py-2 border border-gray-300 rounded-lg">
            <option v-for="o in lifecycleStatusOptions" :key="o" :value="o">{{ t(`lom.status.${o}`, o) }}</option>
          </select>
        </label>
        <label class="block">
          <span class="text-sm font-medium text-gray-700">{{ t('lomEditor.fields.aggregationLevel') }}</span>
          <input v-model.number="general.aggregation_level" type="number" min="1" max="4" class="mt-1 w-full px-3 py-2 border border-gray-300 rounded-lg" />
        </label>
      </div>
      <label class="block">
        <span class="text-sm font-medium text-gray-700">{{ t('lomEditor.fields.coverage') }}</span>
        <input v-model="general.coverage" type="text" class="mt-1 w-full px-3 py-2 border border-gray-300 rounded-lg" />
      </label>
    </section>

    <!-- Classifications -->
    <section class="space-y-4">
      <div class="flex items-center justify-between">
        <h4 class="text-sm font-bold text-secondary-700 uppercase tracking-wider">{{ t('lomEditor.sections.classifications') }}</h4>
        <AppButton variant="ghost" size="sm" @click="addClassification">+ {{ t('lomEditor.actions.addClassification') }}</AppButton>
      </div>
      <p v-if="!classifications.length" class="text-sm text-gray-500">{{ t('lomEditor.noClassifications') }}</p>
      <div v-for="(c, idx) in classifications" :key="idx" class="grid grid-cols-1 md:grid-cols-4 gap-3 items-end border border-gray-100 rounded-lg p-3 bg-gray-50">
        <label class="block">
          <span class="text-xs font-medium text-gray-600">{{ t('lomEditor.fields.purpose') }}</span>
          <select v-model="c.purpose" class="mt-1 w-full px-2 py-1.5 border border-gray-300 rounded-lg text-sm">
            <option v-for="o in classificationPurposeOptions" :key="o" :value="o">{{ t(`lom.purpose.${o}`, o) }}</option>
          </select>
        </label>
        <label class="block">
          <span class="text-xs font-medium text-gray-600">{{ t('lomEditor.fields.taxonSource') }}</span>
          <input v-model="c.taxon_source" type="text" class="mt-1 w-full px-2 py-1.5 border border-gray-300 rounded-lg text-sm" />
        </label>
        <label class="block">
          <span class="text-xs font-medium text-gray-600">{{ t('lomEditor.fields.taxonEntry') }}</span>
          <input v-model="c.taxon_entry" type="text" class="mt-1 w-full px-2 py-1.5 border border-gray-300 rounded-lg text-sm" />
        </label>
        <AppButton variant="danger" size="sm" @click="removeClassification(idx)">{{ t('lomEditor.actions.remove') }}</AppButton>
      </div>
    </section>

    <!-- Save -->
    <div class="flex items-center gap-3 pt-4 border-t border-gray-200">
      <AppButton variant="primary" :loading="saving" :disabled="!!learningTimeError" @click="save">
        <BaseSpinner v-if="saving" class="-ml-1 mr-2 h-4 w-4 text-white" />
        {{ t('lomEditor.actions.save') }}
      </AppButton>
      <AppButton variant="ghost" :disabled="saving" @click="emit('cancel')">{{ t('lomEditor.actions.cancel') }}</AppButton>
      <span v-if="saveOk" class="text-sm text-emerald-700">{{ t('lomEditor.saved') }}</span>
      <span v-if="saveError" class="text-sm text-red-600 truncate">{{ saveError }}</span>
    </div>
  </div>
</template>
