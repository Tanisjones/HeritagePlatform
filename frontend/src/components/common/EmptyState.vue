<script setup lang="ts">
/**
 * EmptyState — the shared "nothing here yet" placeholder for list/collection
 * views (Explore, Learn, routes lists, notifications…). Give it a `title` and
 * optional `description`; drop an action button (e.g. "Create route") into the
 * default slot and a custom illustration into the `icon` slot.
 *
 *   <EmptyState :title="t('routes.empty.title')" :description="t('routes.empty.hint')">
 *     <AppButton @click="...">{{ t('routes.actions.create') }}</AppButton>
 *   </EmptyState>
 */
defineProps<{
  title: string
  description?: string
  /** Tighter padding for smaller containers (cards, sidebars). */
  compact?: boolean
}>()
</script>

<template>
  <div
    class="flex flex-col items-center justify-center text-center"
    :class="compact ? 'py-8 px-4' : 'py-16 px-6'"
  >
    <div class="mb-4 text-gray-300">
      <slot name="icon">
        <svg
          class="h-14 w-14"
          xmlns="http://www.w3.org/2000/svg"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          stroke-width="1.5"
          aria-hidden="true"
        >
          <path
            stroke-linecap="round"
            stroke-linejoin="round"
            d="M20.25 7.5l-.625 10.632a2.25 2.25 0 01-2.247 2.118H6.622a2.25 2.25 0 01-2.247-2.118L3.75 7.5M10 11.25h4M3.375 7.5h17.25c.621 0 1.125-.504 1.125-1.125v-1.5c0-.621-.504-1.125-1.125-1.125H3.375c-.621 0-1.125.504-1.125 1.125v1.5c0 .621.504 1.125 1.125 1.125z"
          />
        </svg>
      </slot>
    </div>
    <h3 class="text-lg font-medium text-gray-900">{{ title }}</h3>
    <p v-if="description" class="mt-1 max-w-md text-sm text-gray-500">{{ description }}</p>
    <div v-if="$slots.default" class="mt-6">
      <slot />
    </div>
  </div>
</template>
