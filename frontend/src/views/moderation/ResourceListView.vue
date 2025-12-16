<script setup lang="ts">
import { ref, onMounted, watch } from 'vue';
import { resourceService } from '@/services/api';
import { useRouter } from 'vue-router';
import { useI18n } from 'vue-i18n';

const { t } = useI18n();
const router = useRouter();

interface Resource {
  id: string;
  title: string;
  heritage_type: { name: string } | null;
  status: string;
  contributor: { first_name: string; last_name: string; email: string } | null;
  created_at: string;
}

const resources = ref<Resource[]>([]);
const loading = ref(false);
const page = ref(1);
const totalPages = ref(1);
const filters = ref({
  status: '',
  search: '',
});

const fetchResources = async () => {
  loading.value = true;
  try {
    const params = {
      page: page.value,
      status: filters.value.status || undefined,
      search: filters.value.search || undefined,
    };
    const response = await resourceService.list(params);
    resources.value = response.data.results;
    if (response.data.count) {
       // Assuming standard DRF pagination size of 10 or 20, let's calculate simplisticly or just rely on next/prev links in a real app
       // For now, let's just use a simple pagination based on count if available, defaulting to next/prev logic if passed
       totalPages.value = Math.ceil(response.data.count / 20); 
    }
  } catch (error) {
    console.error('Error fetching resources:', error);
  } finally {
    loading.value = false;
  }
};

const deleteResource = async (id: string, event?: Event) => {
  event?.preventDefault?.();
  event?.stopPropagation?.();
  if (!confirm(t('moderation.resources.confirmDelete'))) return;
  try {
    await resourceService.delete(id);
    await fetchResources();
  } catch (error) {
    console.error('Error deleting resource:', error);
    alert(t('moderation.resources.deleteError'));
  }
};

const editResource = (id: string, event?: Event) => {
  event?.preventDefault?.();
  event?.stopPropagation?.();
  router.push(`/moderation/resources/${id}/edit`);
};

watch(() => [page.value, filters.value.status], fetchResources);

const debouncedSearch = (e: Event) => {
  filters.value.search = (e.target as HTMLInputElement).value;
  page.value = 1;
  fetchResources();
};

onMounted(fetchResources);
</script>

<template>
  <div class="space-y-6">
    <div class="flex justify-between items-center">
      <h1 class="text-2xl font-bold text-gray-900">{{ t('moderation.resources.title') }}</h1>
    </div>

    <!-- Filters -->
    <div class="bg-white p-4 rounded-lg shadow-sm flex gap-4">
      <input 
        type="text" 
        :placeholder="t('common.search')" 
        @input="debouncedSearch"
        class="border border-gray-300 rounded-md px-3 py-2 w-64"
      />
      <select v-model="filters.status" class="border border-gray-300 rounded-md px-3 py-2">
        <option value="">{{ t('common.allStatus') }}</option>
        <option value="published">{{ t('curatorReview.statusMap.published') }}</option>
        <option value="draft">{{ t('curatorReview.statusMap.draft') }}</option>
        <option value="pending">{{ t('curatorReview.statusMap.pending') }}</option>
        <option value="rejected">{{ t('curatorReview.statusMap.rejected') }}</option>
      </select>
    </div>

    <!-- Table -->
    <div class="bg-white shadow-sm rounded-lg overflow-hidden">
      <table class="min-w-full divide-y divide-gray-200">
        <thead class="bg-gray-50">
          <tr>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">{{ t('common.title') }}</th>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">{{ t('common.type') }}</th>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">{{ t('common.status') }}</th>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">{{ t('common.contributor') }}</th>
            <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">{{ t('common.date') }}</th>
            <th class="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">{{ t('common.actions') }}</th>
          </tr>
        </thead>
        <tbody class="bg-white divide-y divide-gray-200">
          <tr v-if="loading">
            <td colspan="6" class="px-6 py-4 text-center text-gray-500">
              {{ t('common.loading') }}
            </td>
          </tr>
          <tr v-else-if="resources.length === 0">
            <td colspan="6" class="px-6 py-4 text-center text-gray-500">
              {{ t('common.noResults') }}
            </td>
          </tr>
          <tr v-for="resource in resources" :key="resource.id">
            <td class="px-6 py-4 whitespace-nowrap">
              <div class="text-sm font-medium text-gray-900">{{ resource.title }}</div>
              <div class="text-sm text-gray-500">{{ resource.id }}</div>
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
              {{ resource.heritage_type?.name || '-' }}
            </td>
            <td class="px-6 py-4 whitespace-nowrap">
              <span class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full"
                :class="{
                  'bg-green-100 text-green-800': resource.status === 'published',
                  'bg-yellow-100 text-yellow-800': resource.status === 'pending',
                  'bg-red-100 text-red-800': resource.status === 'rejected',
                  'bg-gray-100 text-gray-800': resource.status === 'draft',
                }">
                {{ t(`curatorReview.statusMap.${resource.status}`) }}
              </span>
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
              {{ resource.contributor?.email || 'N/A' }}
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
              {{ new Date(resource.created_at).toLocaleDateString() }}
            </td>
            <td class="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
              <button type="button" @click.stop.prevent="editResource(resource.id, $event)" class="text-indigo-600 hover:text-indigo-900 mr-4">
                {{ t('common.edit') }}
              </button>
              <button type="button" @click.stop.prevent="deleteResource(resource.id, $event)" class="text-red-600 hover:text-red-900">
                {{ t('common.delete') }}
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Pagination -->
    <div class="flex justify-between items-center bg-white p-4 rounded-lg shadow-sm" v-if="totalPages > 1">
      <button 
        @click="page--" 
        :disabled="page === 1"
        class="px-4 py-2 border border-gray-300 rounded-md disabled:opacity-50"
      >
        {{ t('common.previous') }}
      </button>
      <span>{{ t('common.pageInfo', { page: page, total: totalPages }) }}</span>
      <button 
        @click="page++" 
        :disabled="page === totalPages"
        class="px-4 py-2 border border-gray-300 rounded-md disabled:opacity-50"
      >
        {{ t('common.next') }}
      </button>
    </div>
  </div>
</template>
