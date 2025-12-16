<script setup lang="ts">
import { ref, onMounted } from 'vue';
import api from '@/services/api';
import type { HeritageItem } from '@/types/heritage';
import { useI18n } from 'vue-i18n';

const items = ref<HeritageItem[]>([]);
const { t } = useI18n();

const fetchPendingItems = async () => {
  try {
    const response = await api.get('/moderation/');
    items.value = response.data.results;
  } catch (error) {
    console.error('Error fetching pending items:', error);
  }
};

onMounted(fetchPendingItems);

const approveItem = async (id: string) => {
  try {
    await api.post(`/moderation/${id}/approve/`);
    await fetchPendingItems(); // Refresh the list
  } catch (error) {
    console.error('Error approving item:', error);
  }
};

const rejectItem = async (id: string) => {
  const feedback = prompt(t('moderation.prompt.rejectFeedback'));
  if (feedback === null) return; // User cancelled the prompt

  try {
    await api.post(`/moderation/${id}/reject/`, { feedback });
    await fetchPendingItems(); // Refresh the list
  } catch (error) {
    console.error('Error rejecting item:', error);
  }
};
</script>

<template>
  <div>
    <h2>{{ t('moderation.title') }}</h2>
    <table>
      <thead>
        <tr>
          <th>{{ t('moderation.table.title') }}</th>
          <th>{{ t('moderation.table.contributor') }}</th>
          <th>{{ t('moderation.table.status') }}</th>
          <th>{{ t('moderation.table.actions') }}</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="item in items" :key="item.id">
          <td>{{ item.title }}</td>
          <td>{{ item.contributor?.email }}</td>
          <td>{{ item.status }}</td>
          <td>
            <button @click="approveItem(item.id)">{{ t('moderation.approve') }}</button>
            <button @click="rejectItem(item.id)">{{ t('moderation.reject') }}</button>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>
