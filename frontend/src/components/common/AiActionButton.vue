<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import BaseSpinner from './BaseSpinner.vue'

/**
 * AiActionButton — the shared "do something with AI" button used across the
 * contribution wizard (draft, metadata, …). Shows an optional error message,
 * disables + tooltips when AI is unavailable, and swaps the label for a spinner
 * while loading.
 */
const props = defineProps<{
  label: string
  loadingLabel: string
  loading: boolean
  available: boolean
  disabled?: boolean
  error?: string | null
}>()

const emit = defineEmits<{ click: [] }>()
const { t } = useI18n()
</script>

<template>
  <div class="flex items-center justify-end gap-3">
    <div v-if="props.error" class="text-sm text-red-700 bg-red-50 border border-red-200 px-3 py-2 rounded-lg">
      {{ props.error }}
    </div>
    <!-- B3: when AI is off, say so visibly — a hover-only tooltip on a greyed
         button reads as breakage to contributors who never hover it. -->
    <span v-if="!props.available" class="text-xs text-gray-500 italic">
      {{ t('ai.unavailable') }}
    </span>
    <span class="inline-block" :title="!props.available ? t('ai.unavailable') : ''">
      <button
        type="button"
        class="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-primary-600 text-white hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed"
        :disabled="props.loading || props.disabled || !props.available"
        @click="emit('click')"
      >
        <BaseSpinner v-if="props.loading" class="h-4 w-4" />
        <span>{{ props.loading ? props.loadingLabel : props.label }}</span>
      </button>
    </span>
  </div>
</template>
