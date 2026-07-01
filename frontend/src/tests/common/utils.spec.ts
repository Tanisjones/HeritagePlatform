import { describe, expect, it } from 'vitest'
import { unwrapResults } from '@/utils/pagination'
import { extractApiError } from '@/utils/apiError'

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
