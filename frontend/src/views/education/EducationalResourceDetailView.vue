<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { useRoute } from 'vue-router';
import { useI18n } from 'vue-i18n';
import api from '@/services/api';
import { useAsyncAction } from '@/composables/useAsyncAction';
import type { EducationalResource } from '@/types/heritage';
import BaseSpinner from '@/components/common/BaseSpinner.vue';
import ErrorBanner from '@/components/common/ErrorBanner.vue';

const { t } = useI18n();
const route = useRoute();
const resource = ref<EducationalResource | null>(null);
// H.3: unified fetch via the V1 composable.
const { loading, error, run } = useAsyncAction();

const fetchResource = () =>
  run(async () => {
    const response = await api.get(`/educational-resources/${route.params.id}/`);
    resource.value = response.data;
  });

onMounted(fetchResource);
</script>

<template>
  <div class="max-w-4xl mx-auto p-5">
    <div v-if="loading" class="flex justify-center items-center py-12">
      <BaseSpinner class="h-8 w-8 text-primary-600" />
    </div>

    <ErrorBanner v-else-if="error" :message="error" @retry="fetchResource" />

    <div v-else-if="resource" class="bg-white">
      <h1 class="text-3xl font-bold text-gray-900 mb-4">{{ resource.title }}</h1>

      <p class="text-base italic text-gray-600 mb-6">
        {{ t('education.by') }} {{ resource.author?.email }} | {{ resource.resource_type?.name }} | {{ resource.category?.name }}
      </p>

      <div class="prose prose-lg max-w-none text-gray-700 leading-relaxed" v-html="resource.content"></div>
    </div>

    <div v-else class="text-center py-12">
      <p class="text-gray-600">{{ t('common.noResults') }}</p>
    </div>
  </div>
</template>
