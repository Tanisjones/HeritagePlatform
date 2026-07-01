<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import AppButton from './AppButton.vue'

/**
 * ErrorBanner — the shared inline error surface. Replaces the copy-pasted
 * "text-red-700 bg-red-50 border border-red-200" markup and the swallowed
 * console.error()s across ~12 views. Renders nothing when `message` is falsy,
 * so it can be bound directly to a store/composable `error` ref:
 *
 *   <ErrorBanner :message="error" @retry="load" />
 *
 * Emits `retry` only when a listener is attached (a Retry button appears then),
 * and `dismiss` when `dismissible`.
 */
withDefaults(
  defineProps<{
    message?: string | null
    /** Show a Retry button (also requires a @retry listener to do anything). */
    retryable?: boolean
    /** Show a dismiss (×) button. */
    dismissible?: boolean
    /** Tighter spacing for inline/form contexts. */
    dense?: boolean
  }>(),
  { retryable: true, dismissible: false, dense: false },
)

const emit = defineEmits<{ retry: []; dismiss: [] }>()
const { t } = useI18n()
</script>

<template>
  <div
    v-if="message"
    role="alert"
    :class="[
      'flex items-start gap-3 rounded-lg border border-red-200 bg-red-50 text-red-700',
      dense ? 'px-3 py-2 text-sm' : 'px-4 py-3',
    ]"
  >
    <svg
      class="mt-0.5 h-5 w-5 flex-shrink-0 text-red-500"
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 20 20"
      fill="currentColor"
      aria-hidden="true"
    >
      <path
        fill-rule="evenodd"
        d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z"
        clip-rule="evenodd"
      />
    </svg>
    <p class="flex-grow break-words">{{ message }}</p>
    <AppButton
      v-if="retryable"
      variant="ghost"
      size="sm"
      class="!text-red-700 hover:!bg-red-100"
      @click="emit('retry')"
    >
      {{ t('common.retry') }}
    </AppButton>
    <button
      v-if="dismissible"
      type="button"
      class="flex-shrink-0 rounded p-1 text-red-500 hover:bg-red-100 focus:outline-none focus:ring-2 focus:ring-red-400"
      :aria-label="t('common.dismiss')"
      @click="emit('dismiss')"
    >
      <svg class="h-4 w-4" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
        <path d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z" />
      </svg>
    </button>
  </div>
</template>
