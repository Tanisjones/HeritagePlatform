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
type AiErrorKeys = { unavailable?: string; rateLimited?: string; generic?: string }

const DEFAULT_KEYS: Required<AiErrorKeys> = {
  unavailable: 'ai.unavailable',
  rateLimited: 'ai.rateLimited',
  generic: 'ai.genericError',
}

export function useAiError() {
  const { t } = useI18n()
  const { markUnavailable } = useAIAvailability()

  /**
   * @param keys optional i18n key overrides for callers that use their own
   *   message namespace (e.g. the curator review uses curatorReview.aiReview.*).
   */
  function applyAIError(err: any, target: { value: string }, keys: AiErrorKeys = {}) {
    const k = { ...DEFAULT_KEYS, ...keys }
    const status = err?.response?.status
    if (status === 503) {
      target.value = t(k.unavailable)
      markUnavailable()
    } else if (status === 429) {
      target.value = t(k.rateLimited)
    } else {
      target.value = t(k.generic)
    }
  }

  return { applyAIError }
}
