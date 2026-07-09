<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue';
import api, { lessonPlanService, curriculumService } from '@/services/api';
import { useAsyncAction } from '@/composables/useAsyncAction';
import { unwrapResults } from '@/utils/pagination';
import { apiBaseUrl } from '@/utils/apiUrl';
import { iso8601ToMinutes, formatIsoDuration } from '@/utils/duration';
import type { LOMResource, LessonPlan, CurriculumStandard } from '@/types/heritage';
import BaseSpinner from '@/components/common/BaseSpinner.vue';
import ErrorBanner from '@/components/common/ErrorBanner.vue';
import EmptyState from '@/components/common/EmptyState.vue';
import { useI18n } from 'vue-i18n';
import { useToast } from '@/composables/useDialogs';
import { useLomLabels } from '@/composables/useLomLabels';

const { t } = useI18n();
const toast = useToast();
// Shared LOM vocab translators (aliased to keep existing template calls).
const { humanize: humanizeEnum, translate: translateEnum, ageRange } = useLomLabels();
// H.3: unified fetch via the V1 composable.
const { loading, error, run } = useAsyncAction();
const lomResources = ref<LOMResource[]>([]);
const downloadingId = ref<string | null>(null);

// A.6 — published lesson plans, discoverable by curriculum standard.
const plans = ref<LessonPlan[]>([]);
const plansLoading = ref(false);
const planStandard = ref('');
const standardsCatalog = ref<CurriculumStandard[]>([]);
const standardsBySubject = computed(() => {
  const groups = new Map<string, CurriculumStandard[]>();
  for (const std of standardsCatalog.value) {
    const key = std.subject || '—';
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key)!.push(std);
  }
  return groups;
});

async function fetchPlans() {
  plansLoading.value = true;
  try {
    const params: Record<string, any> = { status: 'published', page_size: 6 };
    if (planStandard.value) params.standard = planStandard.value;
    plans.value = unwrapResults<LessonPlan>((await lessonPlanService.list(params)).data);
  } catch {
    plans.value = [];
  } finally {
    plansLoading.value = false;
  }
}

async function loadStandardsCatalog() {
  try {
    standardsCatalog.value = unwrapResults<CurriculumStandard>(
      (await curriculumService.standards()).data,
    );
  } catch {
    standardsCatalog.value = [];
  }
}

watch(planStandard, fetchPlans);

const filters = ref({
  search: '',
  level: 'all',
  resourceType: '',
  context: '',
  difficulty: '',
  language: '',
  ageBand: '',      // '', 'children' (<12), 'teens' (12-17), 'adults' (18+)
  timeBand: '',     // '', 'short' (<30m), 'medium' (30-90m), 'long' (>90m)
  withObjectives: false,
});

// Lowest age mentioned in a free-text range like "12-14" or "18+"; null if none.
const ageLowerBound = (range?: string): number | null => {
  if (!range) return null;
  const m = range.match(/\d+/);
  return m ? Number(m[0]) : null;
};

const tabs = [
    { value: '', label: 'learn.tabs.all' },
    { value: 'school', label: 'learn.tabs.school' },
    { value: 'higher_education', label: 'learn.tabs.higher_education' },
    { value: 'training', label: 'learn.tabs.training' },
];

const setContext = (val: string) => {
    filters.value.context = val;
};

const levelDifficultyMap: Record<string, string[]> = {
  beginner: ['very_easy', 'easy'],
  intermediate: ['medium'],
  advanced: ['difficult', 'very_difficult'],
};

const learningResourceTypes = [
  { value: 'exercise', labelKey: 'learn.resourceTypes.exercise' },
  { value: 'simulation', labelKey: 'learn.resourceTypes.simulation' },
  { value: 'questionnaire', labelKey: 'learn.resourceTypes.questionnaire' },
  { value: 'diagram', labelKey: 'learn.resourceTypes.diagram' },
  { value: 'figure', labelKey: 'learn.resourceTypes.figure' },
  { value: 'graph', labelKey: 'learn.resourceTypes.graph' },
  { value: 'slide', labelKey: 'learn.resourceTypes.slide' },
  { value: 'table', labelKey: 'learn.resourceTypes.table' },
  { value: 'narrative_text', labelKey: 'learn.resourceTypes.narrative_text' },
  { value: 'exam', labelKey: 'learn.resourceTypes.exam' },
  { value: 'experiment', labelKey: 'learn.resourceTypes.experiment' },
  { value: 'problem_statement', labelKey: 'learn.resourceTypes.problem_statement' },
  { value: 'self_assessment', labelKey: 'learn.resourceTypes.self_assessment' },
  { value: 'lecture', labelKey: 'learn.resourceTypes.lecture' },
];



const difficultyOptions = [
  { value: 'very_easy', labelKey: 'learn.difficulties.very_easy' },
  { value: 'easy', labelKey: 'learn.difficulties.easy' },
  { value: 'medium', labelKey: 'learn.difficulties.medium' },
  { value: 'difficult', labelKey: 'learn.difficulties.difficult' },
  { value: 'very_difficult', labelKey: 'learn.difficulties.very_difficult' },
];

const languages = [
  { value: 'es', labelKey: 'learn.languages.es' },
  { value: 'en', labelKey: 'learn.languages.en' },
  { value: 'qu', labelKey: 'learn.languages.qu' },
];

const fetchLom = () =>
  run(async () => {
    const response = await api.get('/lom/');
    lomResources.value = unwrapResults<LOMResource>(response.data);
  });

const downloadScorm = async (resource: LOMResource) => {
  if (!resource.id) return;
  const heritageItemId = resource.heritage_item_id;
  if (!heritageItemId) return;
  downloadingId.value = resource.id;
  try {
    const baseUrl = apiBaseUrl();
    const downloadUrl = `${baseUrl.replace(/\/$/, '')}/education/scorm-packages/${heritageItemId}/download/`;

    // Use a normal browser navigation for the download; Chrome handles ZIP attachments
    // more reliably this way than blob/iframe strategies.
    const link = document.createElement('a');
    link.href = downloadUrl;
    link.target = '_blank';
    link.rel = 'noopener';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  } catch (e) {
    console.error('Download failed', e);
    toast.error(t('learn.labels.downloadError'));
  } finally {
    downloadingId.value = null;
  }
};

const filteredResources = computed(() => {
  return lomResources.value.filter(resource => {
    const edu = resource.educational;
    if (!edu) return false;

    if (filters.value.search) {
      const term = filters.value.search.toLowerCase();
      const haystack = `${resource.title || ''} ${resource.description || ''} ${(resource.keywords || []).join(' ')}`.toLowerCase();
      if (!haystack.includes(term)) return false;
    }

    if (filters.value.level !== 'all') {
      const allowed = levelDifficultyMap[filters.value.level] || [];
      if (!edu.difficulty || !allowed.includes(edu.difficulty)) return false;
    }

    if (filters.value.resourceType && edu.learning_resource_type !== filters.value.resourceType) {
      return false;
    }

    if (filters.value.context && edu.context !== filters.value.context) {
      return false;
    }

    if (filters.value.difficulty && edu.difficulty !== filters.value.difficulty) {
      return false;
    }

    const resourceLanguage = edu.language || resource.language;
    if (filters.value.language && resourceLanguage !== filters.value.language) {
      return false;
    }

    if (filters.value.ageBand) {
      const age = ageLowerBound(edu.typical_age_range);
      if (age === null) return false;
      if (filters.value.ageBand === 'children' && age >= 12) return false;
      if (filters.value.ageBand === 'teens' && (age < 12 || age >= 18)) return false;
      if (filters.value.ageBand === 'adults' && age < 18) return false;
    }

    if (filters.value.timeBand) {
      // iso8601ToMinutes handles the full grammar (incl. weeks/months) and
      // returns 0 for a real zero-length duration; null only for unparseable
      // values, which we exclude from all bands.
      const minutes = iso8601ToMinutes(edu.typical_learning_time);
      if (minutes === null) return false;
      if (filters.value.timeBand === 'short' && minutes >= 30) return false;
      if (filters.value.timeBand === 'medium' && (minutes < 30 || minutes > 90)) return false;
      if (filters.value.timeBand === 'long' && minutes <= 90) return false;
    }

    if (filters.value.withObjectives) {
      const objectives = edu.learning_objectives;
      if (!Array.isArray(objectives) || objectives.length === 0) return false;
    }

    return true;
  });
});

const clearFilters = () => {
  filters.value = {
    search: '',
    level: 'all',
    resourceType: '',
    context: '',
    difficulty: '',
    language: '',
    ageBand: '',
    timeBand: '',
    withObjectives: false,
  };
};

onMounted(() => {
  fetchLom();
  fetchPlans();
  loadStandardsCatalog();
});
</script>

<template>
  <div class="max-w-6xl mx-auto px-4 py-10">
    <header class="mb-8">
      <p class="text-sm font-semibold uppercase tracking-wide text-primary-600">{{ t('learn.header.subtitle') }}</p>
      <h1 class="text-3xl md:text-4xl font-bold text-gray-900 mt-2">{{ t('learn.header.title') }}</h1>
      <p class="text-gray-600 mt-3 max-w-3xl">
        {{ t('learn.header.description') }}
      </p>
    </header>

    <!-- A.6: published lesson plans, filterable by curriculum standard -->
    <section
      v-if="plans.length || planStandard || plansLoading"
      class="mb-10 bg-secondary-50/60 border border-secondary-100 rounded-xl p-5 md:p-6"
    >
      <div class="flex flex-wrap items-center justify-between gap-3 mb-4">
        <div>
          <h2 class="text-xl font-bold text-gray-900">{{ t('learn.plans.title') }}</h2>
          <p class="text-sm text-gray-600">{{ t('learn.plans.description') }}</p>
        </div>
        <div v-if="standardsCatalog.length">
          <label class="sr-only">{{ t('learn.plans.standardFilter') }}</label>
          <select
            v-model="planStandard"
            class="rounded-lg border-gray-300 text-sm focus:border-primary-500 focus:ring-primary-500"
          >
            <option value="">{{ t('learn.plans.allStandards') }}</option>
            <optgroup v-for="[subject, group] in standardsBySubject" :key="subject" :label="subject">
              <option v-for="std in group" :key="std.id" :value="std.code">
                {{ std.code }} · {{ std.grade_level }}
              </option>
            </optgroup>
          </select>
        </div>
      </div>

      <div v-if="plansLoading" class="flex justify-center py-8">
        <BaseSpinner class="h-6 w-6 text-primary-600" />
      </div>
      <div v-else-if="plans.length" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <RouterLink
          v-for="plan in plans"
          :key="plan.id"
          :to="{ name: 'lesson-plan-detail', params: { id: plan.id } }"
          class="block bg-white border border-gray-200 rounded-xl p-4 hover:shadow-md transition-shadow"
        >
          <h3 class="font-semibold text-gray-900">{{ plan.title }}</h3>
          <p v-if="plan.summary" class="mt-1 text-sm text-gray-600 line-clamp-2">{{ plan.summary }}</p>
          <div class="mt-2 flex flex-wrap gap-1.5 text-xs">
            <span v-if="plan.subject" class="px-2 py-0.5 rounded-full bg-gray-100 text-gray-700">{{ plan.subject }}</span>
            <span v-if="plan.grade_level" class="px-2 py-0.5 rounded-full bg-gray-100 text-gray-700">{{ plan.grade_level }}</span>
            <span
              v-for="std in (plan.standards_detail || []).slice(0, 3)"
              :key="std.id"
              class="px-2 py-0.5 rounded-full bg-primary-50 text-primary-700 border border-primary-100"
              :title="std.description"
            >{{ std.code }}</span>
          </div>
          <p class="mt-2 text-xs text-gray-400">
            {{ plan.activities.length }} {{ t('lessonPlans.activitiesCount') }}
          </p>
        </RouterLink>
      </div>
      <p v-else class="text-sm text-gray-500 py-4 text-center">{{ t('learn.plans.emptyForStandard') }}</p>
    </section>

    <!-- Tabs -->
    <div class="mb-6 border-b border-gray-200">
      <nav class="-mb-px flex space-x-8 overflow-x-auto" aria-label="Tabs">
        <button
          v-for="tab in tabs"
          :key="tab.value"
          @click="setContext(tab.value)"
          :class="[
            filters.context === tab.value
              ? 'border-primary-500 text-primary-600'
              : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300',
            'whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm focus:outline-none transition-colors'
          ]"
        >
          {{ t(tab.label) }}
        </button>
      </nav>
    </div>

    <section class="bg-white shadow-sm border border-gray-200 rounded-xl p-5 md:p-6 mb-8">
      <div class="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-4">
        <div class="col-span-1 md:col-span-2">
          <label class="block text-sm font-semibold text-gray-700 mb-1">{{ t('learn.filters.search') }}</label>
          <input
            v-model="filters.search"
            type="text"
            :placeholder="t('learn.filters.searchPlaceholder')"
            class="w-full rounded-lg border-gray-300 focus:border-primary-500 focus:ring-primary-500"
          />
        </div>

        <div>
          <label class="block text-sm font-semibold text-gray-700 mb-1">{{ t('learn.filters.level') }}</label>
          <select
            v-model="filters.level"
            class="w-full rounded-lg border-gray-300 focus:border-primary-500 focus:ring-primary-500"
          >
            <option value="all">{{ t('learn.options.all') }}</option>
            <option value="beginner">{{ t('learn.options.beginner') }}</option>
            <option value="intermediate">{{ t('learn.options.intermediate') }}</option>
            <option value="advanced">{{ t('learn.options.advanced') }}</option>
          </select>
        </div>

        <div>
          <label class="block text-sm font-semibold text-gray-700 mb-1">{{ t('learn.filters.resourceType') }}</label>
          <select
            v-model="filters.resourceType"
            class="w-full rounded-lg border-gray-300 focus:border-primary-500 focus:ring-primary-500"
          >
            <option value="">{{ t('learn.options.allTypes') }}</option>
            <option v-for="type in learningResourceTypes" :key="type.value" :value="type.value">
              {{ t(type.labelKey) }}
            </option>
          </select>
        </div>

        <div>
          <label class="block text-sm font-semibold text-gray-700 mb-1">{{ t('learn.filters.difficulty') }}</label>
          <select
            v-model="filters.difficulty"
            class="w-full rounded-lg border-gray-300 focus:border-primary-500 focus:ring-primary-500"
          >
            <option value="">{{ t('learn.options.any') }}</option>
            <option v-for="option in difficultyOptions" :key="option.value" :value="option.value">
              {{ t(option.labelKey) }}
            </option>
          </select>
        </div>

        <div>
          <label class="block text-sm font-semibold text-gray-700 mb-1">{{ t('learn.filters.language') }}</label>
          <select
            v-model="filters.language"
            class="w-full rounded-lg border-gray-300 focus:border-primary-500 focus:ring-primary-500"
          >
            <option value="">{{ t('learn.options.any') }}</option>
            <option v-for="lang in languages" :key="lang.value" :value="lang.value">
              {{ t(lang.labelKey) }}
            </option>
          </select>
        </div>

        <div>
          <label class="block text-sm font-semibold text-gray-700 mb-1">{{ t('learn.filters.age') }}</label>
          <select
            v-model="filters.ageBand"
            class="w-full rounded-lg border-gray-300 focus:border-primary-500 focus:ring-primary-500"
          >
            <option value="">{{ t('learn.options.any') }}</option>
            <option value="children">{{ t('learn.ageBands.children') }}</option>
            <option value="teens">{{ t('learn.ageBands.teens') }}</option>
            <option value="adults">{{ t('learn.ageBands.adults') }}</option>
          </select>
        </div>

        <div>
          <label class="block text-sm font-semibold text-gray-700 mb-1">{{ t('learn.filters.time') }}</label>
          <select
            v-model="filters.timeBand"
            class="w-full rounded-lg border-gray-300 focus:border-primary-500 focus:ring-primary-500"
          >
            <option value="">{{ t('learn.options.any') }}</option>
            <option value="short">{{ t('learn.timeBands.short') }}</option>
            <option value="medium">{{ t('learn.timeBands.medium') }}</option>
            <option value="long">{{ t('learn.timeBands.long') }}</option>
          </select>
        </div>
      </div>

      <div class="mt-4 flex flex-wrap items-center gap-3">
        <button
          type="button"
          class="inline-flex items-center px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors"
          @click="fetchLom"
        >
          {{ t('learn.filters.refresh') }}
        </button>
        <button
          type="button"
          class="inline-flex items-center px-4 py-2 text-primary-700 border border-primary-100 bg-primary-50 rounded-lg hover:bg-primary-100 transition-colors"
          @click="clearFilters"
        >
          {{ t('learn.filters.clear') }}
        </button>
        <label class="inline-flex items-center gap-2 text-sm text-gray-700">
          <input v-model="filters.withObjectives" type="checkbox" class="rounded border-gray-300 text-primary-600 focus:ring-primary-500" />
          {{ t('learn.filters.withObjectives') }}
        </label>
        <span class="text-sm text-gray-500">{{ t('learn.filters.showing', { count: filteredResources.length, total: lomResources.length }) }}</span>
      </div>
    </section>

    <section>
      <div v-if="loading" class="flex justify-center items-center py-16">
        <BaseSpinner class="h-8 w-8 text-primary-600" />
      </div>

      <ErrorBanner v-else-if="error" :message="error" @retry="fetchLom" />

      <EmptyState
        v-else-if="filteredResources.length === 0"
        :title="t('learn.filters.noResults')"
      />

      <div v-else class="grid grid-cols-1 md:grid-cols-2 gap-6">
        <article
          v-for="resource in filteredResources"
          :key="resource.id"
          class="bg-white border border-gray-200 rounded-xl shadow-sm p-5 hover:shadow-md transition-shadow flex flex-col justify-between"
        >
          <div>
            <header class="mb-3">
                <!-- A.2: the card leads with the TITLE (the internal LOM id was
                     meaningless to learners and teachers). -->
                <div class="flex justify-between items-start gap-2">
                    <h2 class="text-xl font-semibold text-gray-900">{{ resource.title }}</h2>
                    <span v-if="resource.educational?.difficulty"
                        class="flex-shrink-0 px-2 py-0.5 rounded text-xs font-medium border mt-1"
                        :class="{
                            'bg-green-50 text-green-700 border-green-100': ['very_easy', 'easy'].includes(resource.educational?.difficulty || ''),
                            'bg-yellow-50 text-yellow-700 border-yellow-100': ['medium'].includes(resource.educational?.difficulty || ''),
                            'bg-red-50 text-red-700 border-red-100': ['difficult', 'very_difficult'].includes(resource.educational?.difficulty || '')
                        }"
                    >
                       {{
                         translateEnum(
                           `learn.difficulties.${resource.educational.difficulty}`,
                           humanizeEnum(resource.educational.difficulty)
                         )
                       }}
                    </span>
                </div>
                <p class="text-gray-600 text-sm mt-2 line-clamp-3">{{ resource.description }}</p>
            </header>

            <div class="flex flex-wrap gap-2 text-xs text-gray-700 mb-3">
                <span v-if="resource.educational?.learning_resource_type" class="px-2 py-1 rounded-full bg-primary-50 text-primary-700 border border-primary-100">
                {{
                  translateEnum(
                    `learn.resourceTypes.${resource.educational.learning_resource_type}`,
                    humanizeEnum(resource.educational.learning_resource_type)
                  )
                }}
                </span>
                <span v-if="resource.educational?.context" class="px-2 py-1 rounded-full bg-gray-100 text-gray-700">
                {{
                  translateEnum(
                    `learn.tabs.${resource.educational.context}`,
                    humanizeEnum(resource.educational.context)
                  )
                }}
                </span>
                <!-- A.2: localized, self-contained age label ("Todas las edades", "6–12 años") -->
                <span v-if="resource.educational?.typical_age_range" class="px-2 py-1 rounded-full bg-primary-50 text-primary-700 border border-primary-100">
                {{ ageRange(resource.educational.typical_age_range) }}
                </span>
            </div>

            <div class="text-sm text-gray-700 space-y-1 mb-4">
                <p v-if="resource.educational?.typical_learning_time" class="flex items-center">
                    <svg class="w-4 h-4 mr-1 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
                    <!-- A.2: "PT1H" → "1 h" (fall back to the raw value if unparseable) -->
                    <span class="font-medium text-gray-900 mr-1">{{ t('learn.labels.typicalTime') }}:</span>
                    {{ formatIsoDuration(resource.educational.typical_learning_time) || resource.educational.typical_learning_time }}
                </p>
                <p v-if="resource.keywords?.length" class="text-xs text-gray-500">
                    <span class="font-medium text-gray-700">{{ t('learn.labels.keywords') }}:</span> {{ resource.keywords.slice(0, 5).join(', ') }}
                </p>
                <div v-if="resource.educational?.learning_objectives?.length" class="text-xs text-gray-600">
                    <span class="font-medium text-gray-700">{{ t('learn.labels.objectives') }}:</span>
                    <ul class="list-disc list-inside mt-0.5 space-y-0.5">
                      <li v-for="(obj, i) in resource.educational.learning_objectives.slice(0, 3)" :key="i" class="line-clamp-1">{{ obj }}</li>
                    </ul>
                </div>
            </div>
          </div>
          
          <div class="mt-2 pt-4 border-t border-gray-100">
              <button 
                  @click="downloadScorm(resource)" 
                  :disabled="downloadingId === resource.id || !resource.heritage_item_id"
                  class="w-full inline-flex justify-center items-center px-4 py-2 text-sm font-medium text-primary-700 bg-primary-50 border border-primary-100 rounded-lg hover:bg-primary-100 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  <BaseSpinner v-if="downloadingId === resource.id" class="-ml-1 mr-2 h-4 w-4 text-primary-700" />
                  <svg v-else class="mr-2 h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"></path></svg>
                  {{ downloadingId === resource.id ? t('learn.labels.downloading') : t('learn.labels.download') }}
              </button>
          </div>
        </article>
      </div>
    </section>
  </div>
</template>
