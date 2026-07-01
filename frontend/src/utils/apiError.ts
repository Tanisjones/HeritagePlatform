import i18n from '@/i18n'

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
 * When nothing matches (e.g. a network/timeout error whose only `.message` is a
 * technical English string), returns `fallback` — defaulting to the localized
 * `common.errorGeneric` so a Spanish user never sees an English fallback.
 */
export function extractApiError(err: unknown, fallback?: string): string {
  const resolvedFallback = fallback ?? i18n.global.t('common.errorGeneric')
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

  // Note: we deliberately do NOT surface the raw axios `.message` ("Network
  // Error", "timeout of…") — those are untranslated technical strings.
  return resolvedFallback
}
