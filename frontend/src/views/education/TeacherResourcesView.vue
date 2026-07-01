<script setup lang="ts">
/**
 * TeacherResourcesView.vue  (route: /teach, guard: requiresTeacher)
 *
 * Teacher-facing hub for packaging heritage content for the classroom:
 * export a whole cultural route as a single interoperable learning package
 * (SCORM 1.2 / SCORM 2004 / cmi5), and jump to the LOM catalogue (/learn).
 */
import { onMounted, ref } from 'vue';
import { RouterLink } from 'vue-router';
import { routeService, teacherService } from '@/services/api';
import type { HeritageRoute } from '@/types/heritage';
import { useI18n } from 'vue-i18n';

const { t } = useI18n();

const routes = ref<HeritageRoute[]>([]);
const loading = ref(false);
const errorMessage = ref('');
const packagingId = ref<string | null>(null);
const packagingError = ref<string | null>(null);
const selectedFormat = ref<'scorm12' | 'scorm2004' | 'cmi5'>('scorm12');

const formats = [
  { value: 'scorm12', labelKey: 'teach.formats.scorm12' },
  { value: 'scorm2004', labelKey: 'teach.formats.scorm2004' },
  { value: 'cmi5', labelKey: 'teach.formats.cmi5' },
];

const fetchRoutes = async () => {
  try {
    loading.value = true;
    errorMessage.value = '';
    const res = await routeService.list({ status: 'published' });
    routes.value = res.data.results || res.data || [];
  } catch (e) {
    console.error('Error loading routes', e);
    errorMessage.value = t('teach.errors.load');
  } finally {
    loading.value = false;
  }
};

// Trigger a browser download from a blob response.
const saveBlob = (data: Blob, filename: string) => {
  const url = window.URL.createObjectURL(data);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  window.URL.revokeObjectURL(url);
};

const exportRoute = async (route: HeritageRoute) => {
  packagingError.value = null;
  packagingId.value = route.id;
  try {
    const res = await teacherService.downloadRoutePackage(route.id, selectedFormat.value);
    const slug = (route.title || 'route').replace(/[^a-zA-Z0-9._-]+/g, '-').replace(/-+/g, '-');
    const ext = selectedFormat.value === 'cmi5' ? 'zip' : 'zip';
    saveBlob(res.data as Blob, `${slug}-${selectedFormat.value}.${ext}`);
  } catch (e: any) {
    // Blob error bodies need to be read back as text.
    let msg = t('teach.errors.package');
    try {
      if (e?.response?.data instanceof Blob) {
        msg = await (e.response.data as Blob).text();
      }
    } catch { /* keep default */ }
    packagingError.value = msg;
  } finally {
    packagingId.value = null;
  }
};

onMounted(fetchRoutes);
</script>

<template>
  <div class="max-w-6xl mx-auto px-4 py-10">
    <header class="mb-8">
      <p class="text-sm font-semibold uppercase tracking-wide text-primary-600">{{ t('teach.subtitle') }}</p>
      <h1 class="text-3xl md:text-4xl font-bold text-gray-900 mt-2">{{ t('teach.title') }}</h1>
      <p class="text-gray-600 mt-3 max-w-3xl">{{ t('teach.description') }}</p>
      <RouterLink to="/learn" class="inline-block mt-4 text-primary-700 font-medium hover:underline">
        {{ t('teach.browseCatalogue') }} →
      </RouterLink>
    </header>

    <section class="bg-white shadow-sm border border-gray-200 rounded-xl p-5 md:p-6 mb-6">
      <label class="block text-sm font-semibold text-gray-700 mb-1">{{ t('teach.format') }}</label>
      <select v-model="selectedFormat" class="rounded-lg border-gray-300 focus:border-primary-500 focus:ring-primary-500">
        <option v-for="f in formats" :key="f.value" :value="f.value">{{ t(f.labelKey) }}</option>
      </select>
      <p class="text-xs text-gray-500 mt-2">{{ t('teach.formatHelp') }}</p>
    </section>

    <section>
      <h2 class="text-xl font-bold text-gray-900 mb-4">{{ t('teach.routesTitle') }}</h2>

      <div v-if="loading" class="flex justify-center py-16">
        <svg class="animate-spin h-8 w-8 text-primary-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
        </svg>
      </div>

      <div v-else-if="errorMessage" class="bg-red-50 border border-red-200 text-red-800 px-4 py-3 rounded-lg">{{ errorMessage }}</div>

      <div v-else-if="routes.length === 0" class="text-center py-12 text-gray-600">{{ t('teach.noRoutes') }}</div>

      <div v-else class="grid grid-cols-1 md:grid-cols-2 gap-6">
        <article v-for="route in routes" :key="route.id" class="bg-white border border-gray-200 rounded-xl shadow-sm p-5 flex flex-col justify-between">
          <div>
            <h3 class="text-lg font-semibold text-gray-900">{{ route.title }}</h3>
            <p class="text-gray-600 text-sm mt-2 line-clamp-3">{{ route.description }}</p>
          </div>
          <div class="mt-4 pt-4 border-t border-gray-100">
            <button
              @click="exportRoute(route)"
              :disabled="packagingId === route.id"
              class="w-full inline-flex justify-center items-center px-4 py-2 text-sm font-medium text-primary-700 bg-primary-50 border border-primary-100 rounded-lg hover:bg-primary-100 disabled:opacity-50 transition-colors"
            >
              <svg v-if="packagingId === route.id" class="animate-spin -ml-1 mr-2 h-4 w-4 text-primary-700" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path></svg>
              {{ packagingId === route.id ? t('teach.exporting') : t('teach.exportRoute') }}
            </button>
          </div>
        </article>
      </div>

      <p v-if="packagingError" class="mt-4 text-sm text-red-600 break-words">{{ packagingError }}</p>
    </section>
  </div>
</template>
