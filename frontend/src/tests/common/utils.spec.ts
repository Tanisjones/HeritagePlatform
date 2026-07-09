import { describe, expect, it } from 'vitest'
import { unwrapResults } from '@/utils/pagination'
import { extractApiError } from '@/utils/apiError'
import { formatIsoDuration } from '@/utils/duration'

describe('unwrapResults', () => {
  it('returns a bare array as-is', () => {
    expect(unwrapResults([1, 2, 3])).toEqual([1, 2, 3])
  })

  it('unwraps a DRF paginated envelope', () => {
    expect(unwrapResults({ count: 2, results: ['a', 'b'] })).toEqual(['a', 'b'])
  })

  it('returns [] for null/undefined/non-list', () => {
    expect(unwrapResults(null)).toEqual([])
    expect(unwrapResults(undefined)).toEqual([])
    expect(unwrapResults({ detail: 'nope' })).toEqual([])
  })
})

describe('extractApiError', () => {
  it('reads DRF non_field_errors first', () => {
    const err = {
      response: { data: { non_field_errors: ['Bad credentials'], email: ['taken'] } },
    }
    expect(extractApiError(err)).toBe('Bad credentials')
  })

  it('reads the first field error', () => {
    const err = { response: { data: { email: ['This field is required.'] } } }
    expect(extractApiError(err)).toBe('This field is required.')
  })

  it('reads a detail string', () => {
    const err = { response: { data: { detail: 'Not found.' } } }
    expect(extractApiError(err)).toBe('Not found.')
  })

  it('reads a plain string body', () => {
    const err = { response: { data: 'Server exploded' } }
    expect(extractApiError(err)).toBe('Server exploded')
  })

  it('uses an explicit fallback and never surfaces the raw axios message', () => {
    // A technical, untranslated axios message must NOT reach the user.
    expect(extractApiError({ message: 'Network Error' })).not.toBe('Network Error')
    // An explicit (already-localized) fallback wins.
    expect(extractApiError({}, 'Oops')).toBe('Oops')
    expect(extractApiError({ message: 'timeout' }, 'Oops')).toBe('Oops')
  })
})

describe('formatIsoDuration (A.2 — humanized LOM learning time)', () => {
  it('renders hours and minutes', () => {
    expect(formatIsoDuration('PT1H')).toBe('1 h')
    expect(formatIsoDuration('PT45M')).toBe('45 min')
    expect(formatIsoDuration('PT1H30M')).toBe('1 h 30 min')
    expect(formatIsoDuration('PT2H')).toBe('2 h')
  })

  it('handles days and sub-minute edge cases', () => {
    expect(formatIsoDuration('P2D')).toBe('2 d')
    expect(formatIsoDuration('P1DT3H')).toBe('1 d 3 h')
    expect(formatIsoDuration('PT30S')).toBe('1 min') // rounds half-up
    expect(formatIsoDuration('PT20S')).toBe('<1 min')
    expect(formatIsoDuration('PT0S')).toBe('0 min')
  })

  it('returns null for empty or unparseable values (caller falls back)', () => {
    expect(formatIsoDuration('')).toBeNull()
    expect(formatIsoDuration(null)).toBeNull()
    expect(formatIsoDuration('1 hora')).toBeNull()
    expect(formatIsoDuration('PT')).toBeNull()
  })
})
