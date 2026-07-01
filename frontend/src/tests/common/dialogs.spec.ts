import { describe, expect, it, vi, afterEach } from 'vitest'
import { useConfirm, useToast } from '@/composables/useDialogs'

describe('useConfirm', () => {
  it('opens on confirm() and resolves true on accept', async () => {
    const { confirm, _confirmState, _accept } = useConfirm()
    const p = confirm({ message: 'Delete?', danger: true })
    expect(_confirmState.open).toBe(true)
    expect(_confirmState.message).toBe('Delete?')
    expect(_confirmState.danger).toBe(true)
    _accept()
    expect(_confirmState.open).toBe(false)
    await expect(p).resolves.toBe(true)
  })

  it('resolves false on cancel', async () => {
    const { confirm, _cancel } = useConfirm()
    const p = confirm('Sure?')
    _cancel()
    await expect(p).resolves.toBe(false)
  })

  it('accepts a bare string message', async () => {
    const { confirm, _confirmState, _accept } = useConfirm()
    const p = confirm('Just a string')
    expect(_confirmState.message).toBe('Just a string')
    _accept()
    await expect(p).resolves.toBe(true)
  })
})

describe('useToast', () => {
  afterEach(() => {
    vi.useRealTimers()
  })

  it('pushes and auto-dismisses after the timeout', () => {
    vi.useFakeTimers()
    const { success, _toasts } = useToast()
    const before = _toasts.length
    success('Saved!', 1000)
    expect(_toasts.length).toBe(before + 1)
    const added = _toasts[_toasts.length - 1]
    expect(added.kind).toBe('success')
    expect(added.message).toBe('Saved!')
    vi.advanceTimersByTime(1000)
    expect(_toasts.find((t) => t.id === added.id)).toBeUndefined()
  })

  it('error() can be dismissed manually', () => {
    const { error, _toasts, _dismiss } = useToast()
    const id = error('Boom', 0) // 0 = no auto-timeout
    expect(_toasts.find((t) => t.id === id)?.kind).toBe('error')
    _dismiss(id)
    expect(_toasts.find((t) => t.id === id)).toBeUndefined()
  })
})
