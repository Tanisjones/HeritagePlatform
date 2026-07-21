<script setup lang="ts">
/**
 * TeacherResourcesView.vue  (route: /teach, guard: requiresTeacher)
 *
 * A.3 — the teacher dashboard: my recent plans (with status), what's waiting in
 * review, suggested content from the active city's catalog, and "start a plan
 * from a route" — plus the original classroom-packaging tools (export a route
 * as SCORM) and the jump to the LOM catalogue (/learn).
 */
import { computed, onMounted, ref } from 'vue';
import { RouterLink, useRouter } from 'vue-router';
import { routeService, teacherService, lessonPlanService, educationService } from '@/services/api';
import { useCityStore } from '@/stores/city';
import { useCityPath } from '@/composables/useCityPath';
import { useAsyncAction } from '@/composables/useAsyncAction';
import { unwrapResults } from '@/utils/pagination';
import type { HeritageRoute, LessonPlan, LOMResource } from '@/types/heritage';
import { saveBlob, readBlobError, slugifyFilename } from '@/utils/download';
import { useLomLabels } from '@/composables/useLomLabels';
import BaseSpinner from '@/components/common/BaseSpinner.vue';
import ErrorBanner from '@/components/common/ErrorBanner.vue';
import EmptyState from '@/components/common/EmptyState.vue';
import { useI18n } from 'vue-i18n';

const { t } = useI18n();
const router = useRouter();
const { cityPath } = useCityPath();
const cityStore = useCityStore();
const { lom: lomLabel } = useLomLabels();

const routes = ref<HeritageRoute[]>([]);
// H.3: unified fetch via the V1 composable.
const { loading, error, run } = useAsyncAction();
const packagingId = ref<string | null>(null);
const packagingError = ref<string | null>(null);
// Route packages support SCORM 1.2 / 2004 only (cmi5 collections aren't modelled).
const selectedFormat = ref<'scorm12' | 'scorm2004'>('scorm12');

const formats = [
  { value: 'scorm12', labelKey: 'teach.formats.scorm12' },
  { value: 'scorm2004', labelKey: 'teach.formats.scorm2004' },
];

// --- my plans (A.3) ---------------------------------------------------------
const myPlans = ref<LessonPlan[]>([]);
const plansLoading = ref(false);
const inReview = computed(() => myPlans.value.filter((p) => p.status === 'review'));

const statusClass: Record<string, string> = {
  draft: 'bg-gray-100 text-gray-700',
  review: 'bg-yellow-100 text-yellow-800',
  published: 'bg-secondary-100 text-secondary-800',
  archived: 'bg-gray-100 text-gray-500',
};

async function fetchMyPlans() {
  plansLoading.value = true;
  try {
    const res = await lessonPlanService.list({ mine: 1, page_size: 6, ordering: '-updated_at' });
    myPlans.value = unwrapResults<LessonPlan>(res.data);
  } catch {
    myPlans.value = [];
  } finally {
    plansLoading.value = false;
  }
}

// --- suggested content (latest learning objects in the active city) ---------
const suggested = ref<LOMResource[]>([]);
async function fetchSuggested() {
  try {
    const res = await educationService.listLom({ page_size: 4, ordering: '-created_at' });
    suggested.value = unwrapResults<LOMResource>(res.data).slice(0, 4);
  } catch {
    suggested.value = [];
  }
}

const fetchRoutes = () =>
  run(async () => {
    const res = await routeService.list({ status: 'published' });
    routes.value = unwrapResults<HeritageRoute>(res.data);
  });

/** A.3: seed a new lesson plan from a route (prefills the related-route link). */
function planFromRoute(route: HeritageRoute) {
  router.push({ name: 'lesson-plan-new', query: { route: route.id, title: route.title } });
}

const exportRoute = async (route: HeritageRoute) => {
  packagingError.value = null;
  packagingId.value = route.id;
  try {
    const res = await teacherService.downloadRoutePackage(route.id, selectedFormat.value);
    const slug = slugifyFilename(route.title, 'route');
    saveBlob(res.data as Blob, `${slug}-${selectedFormat.value}.zip`);
  } catch (e: any) {
    packagingError.value = await readBlobError(e, t('teach.errors.package'));
  } finally {
    packagingId.value = null;
  }
};

function formatDate(value?: string): string {
  if (!value) return '';
  const dt = new Date(value);
  return isNaN(dt.getTime()) ? '' : dt.toLocaleDateString();
}

onMounted(() => {
  fetchRoutes();
  fetchMyPlans();
  fetchSuggested();
});
</script>

<template>
  <div class="max-w-6xl mx-auto px-4 py-10">
    <header class="mb-8">
      <p class="text-sm font-semibold uppercase tracking-wide text-primary-600">{{ t('teach.subtitle') }}</p>
      <h1 class="text-3xl md:text-4xl font-bold text-gray-900 mt-2">{{ t('teach.title') }}</h1>
      <p class="text-gray-600 mt-3 max-w-3xl">{{ t('teach.description') }}</p>
      <div class="mt-4 flex flex-wrap items-center gap-4">
        <RouterLink :to="{ name: 'lesson-plan-new' }" class="inline-flex items-center px-4 py-2 rounded-lg bg-primary-600 text-white font-medium hover:bg-primary-700">
          + {{ t('teach.newPlan') }}
        </RouterLink>
        <RouterLink to="/teach/plans" class="text-primary-700 font-medium hover:underline">
          {{ t('lessonPlans.title') }} →
        </RouterLink>
        <RouterLink :to="cityPath('/learn')" class="text-primary-700 font-medium hover:underline">
          {{ t('teach.browseCatalogue') }} →
        </RouterLink>
      </div>
    </header>

    <!-- A.3: my recent plans -->
    <section class="mb-8">
      <div class="flex items-center justify-between mb-3">
        <h2 class="text-xl font-bold text-gray-900">{{ t('teach.myPlans') }}</h2>
        <span v-if="inReview.length" class="px-2.5 py-1 rounded-full bg-yellow-100 text-yellow-800 text-xs font-medium">
          {{ t('teach.inReviewCount', { count: inReview.length }) }}
        </span>
      </div>

      <div v-if="plansLoading" class="flex justify-center py-8">
        <BaseSpinner class="h-6 w-6 text-primary-600" />
      </div>
      <EmptyState v-else-if="myPlans.length === 0" :title="t('teach.noPlans')" compact>
        <RouterLink :to="{ name: 'lesson-plan-new' }" class="inline-flex items-center px-4 py-2 rounded-lg bg-primary-600 text-white text-sm font-medium hover:bg-primary-700">
          + {{ t('teach.newPlan') }}
        </RouterLink>
      </EmptyState>
      <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <RouterLink
          v-for="plan in myPlans"
          :key="plan.id"
          :to="{ name: 'lesson-plan-edit', params: { id: plan.id } }"
          class="block bg-white border border-gray-200 rounded-xl shadow-sm p-4 hover:shadow-md transition-shadow"
        >
          <div class="flex items-start justify-between gap-2">
            <h3 class="font-semibold text-gray-900">{{ plan.title }}</h3>
            <span class="flex-shrink-0 px-2 py-0.5 rounded-full text-xs font-medium" :class="statusClass[plan.status]">
              {{ t(`lessonPlans.status.${plan.status}`) }}
            </span>
          </div>
          <div class="mt-2 flex flex-wrap gap-2 text-xs text-gray-500">
            <span v-if="plan.subject">{{ plan.subject }}</span>
            <span v-if="plan.grade_level">· {{ plan.grade_level }}</span>
            <span>· {{ plan.activities.length }} {{ t('lessonPlans.activitiesCount') }}</span>
          </div>
          <p class="mt-2 text-xs text-gray-400">{{ t('teach.updated') }} {{ formatDate(plan.updated_at) }}</p>
        </RouterLink>
      </div>
    </section>

    <!-- A.3: suggested content from the active city's catalog -->
    <section v-if="suggested.length" class="mb-8">
      <h2 class="text-xl font-bold text-gray-900 mb-3">
        {{ t('teach.suggested', { city: cityStore.activeCity?.name ?? '' }) }}
      </h2>
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <RouterLink
          v-for="res in suggested"
          :key="res.id"
          :to="cityPath('/learn')"
          class="block bg-white border border-gray-200 rounded-xl shadow-sm p-4 hover:shadow-md transition-shadow"
        >
          <h3 class="font-medium text-gray-900 line-clamp-2">{{ res.title }}</h3>
          <p v-if="res.educational?.learning_resource_type" class="mt-1 text-xs text-primary-700">
            {{ lomLabel('resource_type', res.educational.learning_resource_type) }}
          </p>
        </RouterLink>
      </div>
    </section>

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
        <BaseSpinner class="h-8 w-8 text-primary-600" />
      </div>

      <ErrorBanner v-else-if="error" :message="error" @retry="fetchRoutes" />

      <EmptyState v-else-if="routes.length === 0" :title="t('teach.noRoutes')" />

      <div v-else class="grid grid-cols-1 md:grid-cols-2 gap-6">
        <article v-for="route in routes" :key="route.id" class="bg-white border border-gray-200 rounded-xl shadow-sm p-5 flex flex-col justify-between">
          <div>
            <h3 class="text-lg font-semibold text-gray-900">{{ route.title }}</h3>
            <p class="text-gray-600 text-sm mt-2 line-clamp-3">{{ route.description }}</p>
          </div>
          <div class="mt-4 pt-4 border-t border-gray-100 flex flex-col sm:flex-row gap-2">
            <!-- A.3: start a lesson plan from this route -->
            <button
              @click="planFromRoute(route)"
              class="flex-1 inline-flex justify-center items-center px-4 py-2 text-sm font-medium text-white bg-primary-600 rounded-lg hover:bg-primary-700 transition-colors"
            >
              {{ t('teach.planFromRoute') }}
            </button>
            <button
              @click="exportRoute(route)"
              :disabled="packagingId === route.id"
              class="flex-1 inline-flex justify-center items-center px-4 py-2 text-sm font-medium text-primary-700 bg-primary-50 border border-primary-100 rounded-lg hover:bg-primary-100 disabled:opacity-50 transition-colors"
            >
              <BaseSpinner v-if="packagingId === route.id" class="-ml-1 mr-2 h-4 w-4 text-primary-700" />
              {{ packagingId === route.id ? t('teach.exporting') : t('teach.exportRoute') }}
            </button>
          </div>
        </article>
      </div>

      <p v-if="packagingError" class="mt-4 text-sm text-red-600 break-words">{{ packagingError }}</p>
    </section>
  </div>
</template>
