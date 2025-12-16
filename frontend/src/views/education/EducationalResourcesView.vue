<script setup lang="ts">
import { ref, onMounted } from 'vue';
import api from '@/services/api';
import type { EducationalResource } from '@/types/heritage';

const resources = ref<EducationalResource[]>([]);
const loading = ref(true);

const fetchResources = async () => {
  try {
    loading.value = true;
    const response = await api.get('/educational-resources/');
    resources.value = response.data.results;
  } catch (error) {
    console.error('Error fetching educational resources:', error);
  } finally {
    loading.value = false;
  }
};

onMounted(fetchResources);
</script>

<template>
  <div class="max-w-6xl mx-auto p-5">
    <h1 class="text-3xl font-bold text-gray-900 mb-6">Educational Resources</h1>

    <div v-if="loading" class="flex justify-center items-center py-12">
      <svg class="animate-spin h-8 w-8 text-primary-600" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
      </svg>
    </div>

    <div v-else-if="resources.length > 0" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
      <div v-for="resource in resources" :key="resource.id" class="bg-white border border-gray-200 rounded-lg shadow hover:shadow-lg transition-shadow p-5">
        <router-link :to="{ name: 'education-detail', params: { id: resource.id } }" class="block">
          <h2 class="text-xl font-semibold text-gray-900 mb-2 hover:text-primary-600 transition-colors">
            {{ resource.title }}
          </h2>
          <p class="text-gray-600 line-clamp-3">{{ resource.description }}</p>
        </router-link>
      </div>
    </div>

    <div v-else class="text-center py-12">
      <p class="text-gray-600">No educational resources found.</p>
    </div>
  </div>
</template>
