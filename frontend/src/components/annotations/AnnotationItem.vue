<script setup lang="ts">
import { computed } from 'vue';

interface Annotation {
  id: string;
  heritage_item: string;
  user_email: string;
  content: string;
  created_at: string;
  updated_at: string;
}

const props = defineProps<{
  annotation: Annotation;
}>();

const formattedDate = computed(() => {
  const date = new Date(props.annotation.created_at);
  return new Intl.DateTimeFormat('es-ES', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  }).format(date);
});

const userInitials = computed(() => {
  const email = props.annotation.user_email;
  return email.charAt(0).toUpperCase();
});
</script>

<template>
  <div class="bg-white border border-gray-200 rounded-lg p-4 hover:shadow-md transition">
    <div class="flex items-start space-x-3">
      <div class="flex-shrink-0">
        <div class="h-10 w-10 rounded-full bg-blue-100 flex items-center justify-center">
          <span class="text-blue-700 font-semibold text-sm">{{ userInitials }}</span>
        </div>
      </div>
      <div class="flex-1 min-w-0">
        <div class="flex items-center justify-between mb-1">
          <p class="text-sm font-medium text-gray-900">
            {{ annotation.user_email }}
          </p>
          <p class="text-sm text-gray-500">{{ formattedDate }}</p>
        </div>
        <p class="text-gray-700 whitespace-pre-wrap">{{ annotation.content }}</p>
      </div>
    </div>
  </div>
</template>
