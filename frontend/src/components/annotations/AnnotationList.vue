<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { useAuthStore } from '@/stores/auth';
import { useI18n } from 'vue-i18n';
import api from '@/services/api';
import AnnotationItem from './AnnotationItem.vue';
import AnnotationForm from './AnnotationForm.vue';

interface Annotation {
  id: string;
  heritage_item: string;
  user_email: string;
  content: string;
  created_at: string;
  updated_at: string;
}

const props = defineProps<{
  heritageItemId: string;
}>();

const { t } = useI18n();
const authStore = useAuthStore();
const annotations = ref<Annotation[]>([]);
const loading = ref(true);
const showForm = ref(false);

const fetchAnnotations = async () => {
  try {
    loading.value = true;
    const response = await api.get('/annotations/', {
      params: { heritage_item: props.heritageItemId }
    });
    annotations.value = response.data.results || response.data;
  } catch (error) {
    console.error('Error fetching annotations:', error);
  } finally {
    loading.value = false;
  }
};

const handleAnnotationCreated = (newAnnotation: Annotation) => {
  annotations.value.unshift(newAnnotation);
  showForm.value = false;
};

onMounted(fetchAnnotations);
</script>

<template>
  <div class="mt-8 pt-6 border-t border-gray-200">
    <div class="flex justify-between items-center mb-6">
      <h2 class="text-2xl font-bold text-gray-900">
        {{ t('heritage.annotations.title') }}
        <span class="text-lg text-gray-500 font-normal">({{ annotations.length }})</span>
      </h2>
      <button
        v-if="authStore.isAuthenticated && !showForm"
        @click="showForm = true"
        class="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition font-medium"
      >
        {{ t('heritage.annotations.add') }}
      </button>
    </div>

    <div v-if="showForm" class="mb-6">
      <AnnotationForm
        :heritage-item-id="heritageItemId"
        @created="handleAnnotationCreated"
        @cancel="showForm = false"
      />
    </div>

    <div v-if="loading" class="flex justify-center py-8">
      <svg class="animate-spin h-8 w-8 text-blue-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
      </svg>
    </div>

    <div v-else-if="annotations.length === 0" class="text-center py-12 bg-gray-50 rounded-lg">
      <svg xmlns="http://www.w3.org/2000/svg" class="h-16 w-16 mx-auto text-gray-400 mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
      </svg>
      <p class="text-gray-600 text-lg mb-2">{{ t('heritage.annotations.empty') }}</p>
      <p class="text-gray-500">{{ t('heritage.annotations.emptyDesc') }}</p>
    </div>

    <div v-else class="space-y-4">
      <AnnotationItem
        v-for="annotation in annotations"
        :key="annotation.id"
        :annotation="annotation"
      />
    </div>

    <div v-if="!authStore.isAuthenticated" class="mt-6 bg-blue-50 border border-blue-200 rounded-lg p-4">
      <p class="text-blue-800">
        <router-link to="/login" class="font-medium underline hover:text-blue-900">{{ t('heritage.annotations.loginLink') }}</router-link>
        {{ t('heritage.annotations.loginReq') }}
      </p>
    </div>
  </div>
</template>
