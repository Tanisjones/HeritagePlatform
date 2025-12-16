<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import api from '@/services/api';
import type { LOMResource } from '@/types/heritage';
import { useI18n } from 'vue-i18n';

const { t } = useI18n();
const loading = ref(false);
const errorMessage = ref('');
const lomResources = ref<LOMResource[]>([]);
const downloadingId = ref<string | null>(null);

const humanizeEnum = (value: string) => value.replace(/_/g, ' ');
const translateEnum = (key: string, fallback: string) => {
  const translated = t(key);
  return translated === key ? fallback : translated;
};

const filters = ref({
  search: '',
  level: 'all',
  resourceType: '',
  context: '',
  difficulty: '',
  language: '',
});

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

const fetchLom = async () => {
  try {
    loading.value = true;
    errorMessage.value = '';
    const response = await api.get('/lom/');
    lomResources.value = response.data.results || response.data || [];
  } catch (error) {
    console.error('Error fetching LOM resources', error);
    errorMessage.value = t('learn.labels.loadError');
  } finally {
    loading.value = false;
  }
};

const downloadScorm = async (resource: LOMResource) => {
  if (!resource.id) return;
  const heritageItemId = resource.heritage_item_id;
  if (!heritageItemId) return;
  downloadingId.value = resource.id;
  try {
    const baseUrl = api.defaults.baseURL || (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1');
    const downloadUrl = `${String(baseUrl).replace(/\/$/, '')}/education/scorm-packages/${heritageItemId}/download/`;

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
    alert(t('learn.labels.downloadError'));
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
  };
};

onMounted(fetchLom);
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
        <span class="text-sm text-gray-500">{{ t('learn.filters.showing', { count: filteredResources.length, total: lomResources.length }) }}</span>
      </div>
    </section>

    <section>
      <div v-if="loading" class="flex justify-center items-center py-16">
        <svg class="animate-spin h-8 w-8 text-primary-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
        </svg>
      </div>

      <div v-else-if="errorMessage" class="bg-red-50 border border-red-200 text-red-800 px-4 py-3 rounded-lg">
        {{ errorMessage }}
      </div>

      <div v-else-if="filteredResources.length === 0" class="text-center py-12 text-gray-600">
        {{ t('learn.filters.noResults') }}
      </div>

      <div v-else class="grid grid-cols-1 md:grid-cols-2 gap-6">
        <article
          v-for="resource in filteredResources"
          :key="resource.id"
          class="bg-white border border-gray-200 rounded-xl shadow-sm p-5 hover:shadow-md transition-shadow flex flex-col justify-between"
        >
          <div>
            <header class="mb-3">
                <div class="flex justify-between items-start">
                    <p class="text-xs uppercase tracking-wide text-primary-600 font-semibold">LOM {{ resource.id.slice(0, 8) }}</p>
                    <span v-if="resource.educational?.difficulty" 
                        class="px-2 py-0.5 rounded text-xs font-medium border"
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
                <h2 class="text-xl font-semibold text-gray-900 mt-1">{{ resource.title }}</h2>
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
                <span v-if="resource.educational?.typical_age_range" class="px-2 py-1 rounded-full bg-indigo-50 text-indigo-700 border border-indigo-100">
                {{ t('learn.labels.ages') }} {{ resource.educational.typical_age_range }}
                </span>
            </div>

            <div class="text-sm text-gray-700 space-y-1 mb-4">
                <p v-if="resource.educational?.typical_learning_time" class="flex items-center">
                    <svg class="w-4 h-4 mr-1 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
                    <span class="font-medium text-gray-900 mr-1">{{ t('learn.labels.typicalTime') }}:</span> {{ resource.educational.typical_learning_time }}
                </p>
                <p v-if="resource.keywords?.length" class="text-xs text-gray-500">
                    <span class="font-medium text-gray-700">{{ t('learn.labels.keywords') }}:</span> {{ resource.keywords.slice(0, 5).join(', ') }}
                </p>
            </div>
          </div>
          
          <div class="mt-2 pt-4 border-t border-gray-100">
              <button 
                  @click="downloadScorm(resource)" 
                  :disabled="downloadingId === resource.id || !resource.heritage_item_id"
                  class="w-full inline-flex justify-center items-center px-4 py-2 text-sm font-medium text-primary-700 bg-primary-50 border border-primary-100 rounded-lg hover:bg-primary-100 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                >
                  <svg v-if="downloadingId === resource.id" class="animate-spin -ml-1 mr-2 h-4 w-4 text-primary-700" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>
                  <svg v-else class="mr-2 h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"></path></svg>
                  {{ downloadingId === resource.id ? t('learn.labels.downloading') : t('learn.labels.download') }}
              </button>
          </div>
        </article>
      </div>
    </section>
  </div>
</template>
