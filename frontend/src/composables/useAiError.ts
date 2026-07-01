import { useI18n } from 'vue-i18n'
import { useAIAvailability } from '@/services/aiAvailability'

/**
 * Shared mapping of an AI-request error to a localized message, used by every
 * component that calls an aiService.* endpoint (contribution wizard, LOM editor,
 * curator review). 503 → service unavailable (also marks the service down so the
 * UI hides AI actions), 429 → rate-limited, anything else → generic error.
 *
 * Usage:
 *   const { applyAIError } = useAiError()
 *   catch (err) { applyAIError(err, someErrorRef) }
 */
export function useAiError() {
  const { t } = useI18n()
  const { markUnavailable } = useAIAvailability()

  function applyAIError(err: any, target: { value: string }) {
    const status = err?.response?.status
    if (status === 503) {
      target.value = t('ai.unavailable')
      markUnavailable()
    } else if (status === 429) {
      target.value = t('ai.rateLimited')
    } else {
      target.value = t('ai.genericError')
    }
  }

  return { applyAIError }
}
