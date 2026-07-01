<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { useI18n } from 'vue-i18n';
import api from '@/services/api';
import { useAsyncAction } from '@/composables/useAsyncAction';
import { unwrapResults } from '@/utils/pagination';
import type { EducationalResource } from '@/types/heritage';
import BaseSpinner from '@/components/common/BaseSpinner.vue';
import ErrorBanner from '@/components/common/ErrorBanner.vue';
import EmptyState from '@/components/common/EmptyState.vue';

const { t } = useI18n();
const resources = ref<EducationalResource[]>([]);
// H.3: unified fetch (loading/error/extractApiError) via the V1 composable.
const { loading, error, run } = useAsyncAction();

const fetchResources = () =>
  run(async () => {
    const response = await api.get('/educational-resources/');
    resources.value = unwrapResults<EducationalResource>(response.data);
  });

onMounted(fetchResources);
</script>

<template>
  <div class="max-w-6xl mx-auto p-5">
    <h1 class="text-3xl font-bold text-gray-900 mb-6">{{ t('education.resourcesTitle') }}</h1>

    <ErrorBanner :message="error" @retry="fetchResources" />

    <div v-if="loading" class="flex justify-center items-center py-12">
      <BaseSpinner class="h-8 w-8 text-primary-600" />
    </div>

    <div v-else-if="!error && resources.length > 0" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
      <div v-for="resource in resources" :key="resource.id" class="bg-white border border-gray-200 rounded-lg shadow hover:shadow-lg transition-shadow p-5">
        <router-link :to="{ name: 'education-detail', params: { id: resource.id } }" class="block">
          <h2 class="text-xl font-semibold text-gray-900 mb-2 hover:text-primary-600 transition-colors">
            {{ resource.title }}
          </h2>
          <p class="text-gray-600 line-clamp-3">{{ resource.description }}</p>
        </router-link>
      </div>
    </div>

    <EmptyState
      v-else-if="!error"
      :title="t('common.noResults')"
    />
  </div>
</template>
