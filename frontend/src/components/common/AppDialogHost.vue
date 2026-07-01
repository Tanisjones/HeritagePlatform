<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { useConfirm, useToast } from '@/composables/useDialogs'
import AppButton from './AppButton.vue'

/**
 * AppDialogHost — mounted once in App.vue. Renders the app-wide confirm modal
 * and the toast stack driven by the `useConfirm` / `useToast` singletons, so
 * any component can raise dialogs without local modal state. Replaces the
 * native alert()/confirm() calls that used to litter the views.
 */
const { t } = useI18n()
const { _confirmState: dialog, _accept, _cancel } = useConfirm()
const { _toasts: toasts, _dismiss } = useToast()

const toastClasses: Record<string, string> = {
  success: 'bg-secondary-600 text-white',
  error: 'bg-red-600 text-white',
  info: 'bg-gray-800 text-white',
}
</script>

<template>
  <!-- Confirm dialog -->
  <Teleport to="body">
    <Transition
      enter-active-class="transition ease-out duration-150"
      enter-from-class="opacity-0"
      leave-active-class="transition ease-in duration-100"
      leave-to-class="opacity-0"
    >
      <div
        v-if="dialog.open"
        class="fixed inset-0 z-[1000] flex items-center justify-center bg-black/50 p-4"
        role="dialog"
        aria-modal="true"
        @click.self="_cancel"
        @keydown.esc="_cancel"
      >
        <div class="w-full max-w-md rounded-xl bg-white p-6 shadow-xl">
          <h3 v-if="dialog.title" class="mb-2 text-lg font-semibold text-gray-900">
            {{ dialog.title }}
          </h3>
          <p class="text-gray-700">{{ dialog.message }}</p>
          <div class="mt-6 flex justify-end gap-3">
            <AppButton variant="ghost" @click="_cancel">
              {{ dialog.cancelLabel || t('common.cancel') }}
            </AppButton>
            <AppButton :variant="dialog.danger ? 'danger' : 'primary'" @click="_accept">
              {{ dialog.confirmLabel || t('common.confirm') }}
            </AppButton>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>

  <!-- Toast stack -->
  <Teleport to="body">
    <div class="pointer-events-none fixed bottom-4 right-4 z-[1100] flex flex-col gap-2">
      <TransitionGroup
        enter-active-class="transition ease-out duration-200"
        enter-from-class="opacity-0 translate-y-2"
        leave-active-class="transition ease-in duration-150"
        leave-to-class="opacity-0"
      >
        <div
          v-for="toast in toasts"
          :key="toast.id"
          class="pointer-events-auto flex items-center gap-3 rounded-lg px-4 py-3 shadow-lg"
          :class="toastClasses[toast.kind]"
          role="status"
        >
          <span class="text-sm font-medium">{{ toast.message }}</span>
          <button
            type="button"
            class="rounded p-0.5 opacity-80 hover:opacity-100 focus:outline-none"
            :aria-label="t('common.dismiss')"
            @click="_dismiss(toast.id)"
          >
            <svg class="h-4 w-4" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
              <path d="M6.28 5.22a.75.75 0 00-1.06 1.06L8.94 10l-3.72 3.72a.75.75 0 101.06 1.06L10 11.06l3.72 3.72a.75.75 0 101.06-1.06L11.06 10l3.72-3.72a.75.75 0 00-1.06-1.06L10 8.94 6.28 5.22z" />
            </svg>
          </button>
        </div>
      </TransitionGroup>
    </div>
  </Teleport>
</template>
