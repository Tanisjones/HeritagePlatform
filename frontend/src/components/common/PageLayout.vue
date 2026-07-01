<script setup lang="ts">
import { computed } from 'vue'
import BaseSpinner from './BaseSpinner.vue'
import ErrorBanner from './ErrorBanner.vue'

/**
 * PageLayout — the standard view shell. Wraps content in the recurring
 * `max-w-* mx-auto px-* py-*` container and, optionally, orchestrates the
 * loading / error / empty triad so views stop hand-rolling it:
 *
 *   <PageLayout :loading="loading" :error="error" @retry="load">
 *     ...page content...
 *   </PageLayout>
 *
 * When `loading` is true a centered spinner shows; when `error` is set an
 * ErrorBanner shows (with Retry re-emitted as `retry`); otherwise the default
 * slot renders. Pass `bare` to skip the triad and only get the container.
 */
const props = withDefaults(
  defineProps<{
    maxWidth?: '3xl' | '4xl' | '5xl' | '6xl' | '7xl' | 'full'
    loading?: boolean
    error?: string | null
    /** Skip the loading/error orchestration; only apply the container. */
    bare?: boolean
    /** Show a Retry button on the error banner. */
    retryable?: boolean
  }>(),
  { maxWidth: '6xl', loading: false, error: null, bare: false, retryable: true },
)

defineEmits<{ retry: [] }>()

const maxWidthClass = computed(
  () =>
    ({
      '3xl': 'max-w-3xl',
      '4xl': 'max-w-4xl',
      '5xl': 'max-w-5xl',
      '6xl': 'max-w-6xl',
      '7xl': 'max-w-7xl',
      full: 'max-w-full',
    })[props.maxWidth],
)
</script>

<template>
  <div class="mx-auto px-4 py-8 md:px-6" :class="maxWidthClass">
    <template v-if="bare">
      <slot />
    </template>
    <template v-else>
      <div v-if="loading" class="flex justify-center py-20">
        <BaseSpinner class="h-10 w-10 text-primary-600" />
      </div>
      <ErrorBanner v-else-if="error" :message="error" :retryable="retryable" @retry="$emit('retry')" />
      <slot v-else />
    </template>
  </div>
</template>
