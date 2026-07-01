import { ref, watch, type Ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { isValidIso8601Duration, looksLikeMonthsNotMinutes } from '@/utils/duration'

/**
 * Shared client-side validation for an ISO-8601 learning-time input, used by the
 * contribution wizard and the LOM editor so both agree on what's valid and warn
 * identically. Returns a reactive error message ref (empty when the value is OK):
 *   - invalid ISO-8601 syntax → invalidKey
 *   - the "P30M means 30 months, not minutes" footgun → monthsKey
 *
 * Usage:
 *   const timeError = useDurationValidation(
 *     () => educational.typical_learning_time,
 *     { invalidKey: 'lomEditor.errors.duration', monthsKey: 'lomEditor.errors.months' },
 *   )
 */
export function useDurationValidation(
  source: Ref<string> | (() => string | undefined | null),
  keys: { invalidKey: string; monthsKey: string },
): Ref<string> {
  const { t } = useI18n()
  const error = ref('')

  watch(source, (value) => {
    if (value && !isValidIso8601Duration(value)) {
      error.value = t(keys.invalidKey)
    } else if (looksLikeMonthsNotMinutes(value)) {
      error.value = t(keys.monthsKey)
    } else {
      error.value = ''
    }
  }, { immediate: true })

  return error
}
