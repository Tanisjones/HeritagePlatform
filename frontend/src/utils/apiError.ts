/**
 * extractApiError — turn an axios/DRF error into a human-readable string.
 *
 * DRF returns validation errors in a few shapes; this collapses them to the
 * first useful message, matching the ad-hoc logic that used to live inline in
 * Login/Register:
 *   - `{ "non_field_errors": ["msg"] }`  → "msg"
 *   - `{ "field": ["msg"] }`             → "msg"
 *   - `{ "detail": "msg" }`              → "msg"
 *   - `{ "field": "msg" }`               → "msg"
 * Falls back to `fallback` (or the error's own message) when nothing matches.
 */
export function extractApiError(err: unknown, fallback = 'Something went wrong'): string {
  const anyErr = err as { response?: { data?: unknown }; message?: string }
  const data = anyErr?.response?.data

  if (data && typeof data === 'object') {
    const record = data as Record<string, unknown>
    if (typeof record.detail === 'string') return record.detail

    // First field error, preferring non_field_errors.
    const keys = Object.keys(record)
    const ordered = keys.includes('non_field_errors')
      ? ['non_field_errors', ...keys.filter((k) => k !== 'non_field_errors')]
      : keys
    for (const key of ordered) {
      const value = record[key]
      if (Array.isArray(value) && value.length && typeof value[0] === 'string') {
        return value[0]
      }
      if (typeof value === 'string' && value) {
        return value
      }
    }
  } else if (typeof data === 'string' && data) {
    return data
  }

  return anyErr?.message || fallback
}
