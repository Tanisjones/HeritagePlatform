<script setup lang="ts">
defineProps<{
  padding?: 'none' | 'sm' | 'md' | 'lg'
  hoverable?: boolean
}>()
</script>

<template>
  <div
    :class="[
      'bg-white rounded-lg shadow-md overflow-hidden',
      {
        'p-3': padding === 'sm',
        'p-4': !padding || padding === 'md',
        'p-6': padding === 'lg',
        'hover:shadow-lg transition-shadow cursor-pointer': hoverable,
      }
    ]"
  >
    <slot />
  </div>
</template>
