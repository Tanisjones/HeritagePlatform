import { reactive, readonly } from 'vue'

/**
 * App-wide replacement for the native `alert()` / `confirm()` dialogs.
 *
 * Two singletons live here so any component (or store) can trigger UI without
 * prop-drilling: a promise-returning confirm dialog and a transient toast queue.
 * A single <AppDialogHost> mounted once in App.vue renders both.
 *
 *   const { confirm } = useConfirm()
 *   if (await confirm({ message: t('routesUi.builder.confirmDelete'), danger: true })) { ... }
 *
 *   const toast = useToast()
 *   toast.success(t('common.saved'))
 *   toast.error(t('common.errorSaving'))
 */

// ── Confirm ────────────────────────────────────────────────────────────────

export interface ConfirmOptions {
  message: string
  title?: string
  /** Label for the confirm button (defaults to common.confirm). */
  confirmLabel?: string
  /** Label for the cancel button (defaults to common.cancel). */
  cancelLabel?: string
  /** Style the confirm button as destructive (red). */
  danger?: boolean
}

interface ConfirmState extends ConfirmOptions {
  open: boolean
  _resolve: ((ok: boolean) => void) | null
}

const confirmState = reactive<ConfirmState>({
  open: false,
  message: '',
  title: undefined,
  confirmLabel: undefined,
  cancelLabel: undefined,
  danger: false,
  _resolve: null,
})

export function useConfirm() {
  function confirm(options: ConfirmOptions | string): Promise<boolean> {
    const opts = typeof options === 'string' ? { message: options } : options
    // If a previous confirm is somehow still open, resolve it as cancelled.
    if (confirmState._resolve) confirmState._resolve(false)
    confirmState.message = opts.message
    confirmState.title = opts.title
    confirmState.confirmLabel = opts.confirmLabel
    confirmState.cancelLabel = opts.cancelLabel
    confirmState.danger = opts.danger ?? false
    confirmState.open = true
    return new Promise<boolean>((resolve) => {
      confirmState._resolve = resolve
    })
  }

  function _settle(ok: boolean) {
    if (!confirmState.open) return
    confirmState.open = false
    const resolve = confirmState._resolve
    confirmState._resolve = null
    resolve?.(ok)
  }

  return {
    confirm,
    /** Internal — used by AppDialogHost only. */
    _confirmState: readonly(confirmState),
    _accept: () => _settle(true),
    _cancel: () => _settle(false),
  }
}

// ── Toasts ─────────────────────────────────────────────────────────────────

export type ToastKind = 'success' | 'error' | 'info'

export interface Toast {
  id: number
  kind: ToastKind
  message: string
}

const toasts = reactive<Toast[]>([])
let nextToastId = 1
const DEFAULT_TIMEOUT_MS = 4000

function push(kind: ToastKind, message: string, timeout = DEFAULT_TIMEOUT_MS): number {
  const id = nextToastId++
  toasts.push({ id, kind, message })
  if (timeout > 0) {
    // window.setTimeout so tests can fake timers without pulling in Node types.
    window.setTimeout(() => dismissToast(id), timeout)
  }
  return id
}

function dismissToast(id: number) {
  const i = toasts.findIndex((t) => t.id === id)
  if (i !== -1) toasts.splice(i, 1)
}

export function useToast() {
  return {
    success: (message: string, timeout?: number) => push('success', message, timeout),
    error: (message: string, timeout?: number) => push('error', message, timeout),
    info: (message: string, timeout?: number) => push('info', message, timeout),
    /** Internal — used by AppDialogHost only. */
    _toasts: readonly(toasts),
    _dismiss: dismissToast,
  }
}
