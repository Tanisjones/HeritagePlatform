<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { useRoute } from 'vue-router';
import api from '@/services/api';
import type { EducationalResource } from '@/types/heritage';

const route = useRoute();
const resource = ref<EducationalResource | null>(null);
const loading = ref(true);

const fetchResource = async () => {
  const id = route.params.id;
  try {
    loading.value = true;
    const response = await api.get(`/educational-resources/${id}/`);
    resource.value = response.data;
  } catch (error) {
    console.error('Error fetching educational resource:', error);
  } finally {
    loading.value = false;
  }
};

onMounted(fetchResource);
</script>

<template>
  <div class="max-w-4xl mx-auto p-5">
    <div v-if="loading" class="flex justify-center items-center py-12">
      <svg class="animate-spin h-8 w-8 text-primary-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
      </svg>
    </div>

    <div v-else-if="resource" class="bg-white">
      <h1 class="text-3xl font-bold text-gray-900 mb-4">{{ resource.title }}</h1>

      <p class="text-base italic text-gray-600 mb-6">
        By {{ resource.author?.email }} | {{ resource.resource_type?.name }} | {{ resource.category?.name }}
      </p>

      <div class="prose prose-lg max-w-none text-gray-700 leading-relaxed" v-html="resource.content"></div>
    </div>

    <div v-else class="text-center py-12">
      <p class="text-gray-600">Resource not found.</p>
    </div>
  </div>
</template>
