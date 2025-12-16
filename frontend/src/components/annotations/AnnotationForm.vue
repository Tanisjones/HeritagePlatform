<script setup lang="ts">
import { ref } from 'vue';
import { useI18n } from 'vue-i18n';
import api from '@/services/api';

const props = defineProps<{
  heritageItemId: string;
}>();

const emit = defineEmits<{
  created: [annotation: any];
  cancel: [];
}>();

const { t } = useI18n();
const content = ref('');
const submitting = ref(false);
const error = ref('');

const submitAnnotation = async () => {
  if (!content.value.trim()) {
    error.value = t('heritage.annotations.form.errorEmpty');
    return;
  }

  try {
    submitting.value = true;
    error.value = '';

    const response = await api.post('/annotations/', {
      heritage_item: props.heritageItemId,
      content: content.value.trim()
    });

    emit('created', response.data);
    content.value = '';
  } catch (err: any) {
    console.error('Error creating annotation:', err);
    error.value = err.response?.data?.detail || t('heritage.annotations.form.errorSubmit');
  } finally {
    submitting.value = false;
  }
};

const handleCancel = () => {
  content.value = '';
  error.value = '';
  emit('cancel');
};
</script>

<template>
  <div class="bg-gray-50 border border-gray-300 rounded-lg p-4">
    <h3 class="text-lg font-semibold text-gray-900 mb-3">{{ t('heritage.annotations.form.title') }}</h3>

    <div v-if="error" class="mb-4 bg-red-50 border border-red-200 text-red-800 px-4 py-3 rounded">
      {{ error }}
    </div>

    <textarea
      v-model="content"
      rows="4"
      class="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
      :placeholder="t('heritage.annotations.form.placeholder')"
      :disabled="submitting"
    ></textarea>

    <div class="flex justify-end space-x-3 mt-3">
      <button
        @click="handleCancel"
        :disabled="submitting"
        class="px-4 py-2 text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition disabled:opacity-50"
      >
        {{ t('heritage.annotations.form.cancel') }}
      </button>
      <button
        @click="submitAnnotation"
        :disabled="submitting || !content.trim()"
        class="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition disabled:opacity-50 disabled:cursor-not-allowed"
      >
        <span v-if="submitting">{{ t('heritage.annotations.form.submitting') }}</span>
        <span v-else>{{ t('heritage.annotations.form.submit') }}</span>
      </button>
    </div>

    <p class="text-sm text-gray-600 mt-3">
      <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 inline mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
      </svg>
      {{ t('heritage.annotations.form.reward') }}
    </p>
  </div>
</template>
