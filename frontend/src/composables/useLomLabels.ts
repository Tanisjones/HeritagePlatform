import { useI18n } from 'vue-i18n'

/**
 * useLomLabels — the shared translator for IEEE-LOM controlled-vocabulary
 * values (difficulty, context, resource type, interactivity…). These come off
 * the API as machine tokens like `higher_education`; the UI wants a localized
 * label, falling back to a de-underscored version when no translation exists.
 *
 * Unifies the `translateLom` / `translateEnum` / `humanizeEnum` helpers that
 * were copy-pasted into HeritageDetailView, LearnView, LomEditor, etc.
 *
 *   const { lom, humanize, translate } = useLomLabels()
 *   lom('difficulty', edu.difficulty)          // → "Medium" / "Medio"
 *   humanize('higher_education')               // → "higher education"
 */
export function useLomLabels() {
  const { t, te } = useI18n()

  /** "higher_education" → "higher education". */
  function humanize(value: string | null | undefined): string {
    return (value ?? '').replace(/_/g, ' ')
  }

  /**
   * Translate a LOM vocab value under the `lom.<category>.<value>` namespace,
   * falling back to the humanized token. Empty values yield `fallbackKey`
   * (default `heritage.detail.na`).
   */
  function lom(
    category: string,
    value: string | null | undefined,
    fallbackKey = 'heritage.detail.na',
  ): string {
    if (!value) return t(fallbackKey)
    const key = `lom.${category}.${value}`
    return te(key) ? t(key) : humanize(value)
  }

  /**
   * Translate an explicit i18n `key`, falling back to `fallback` when the key
   * is missing (mirrors LearnView's `translateEnum`).
   */
  function translate(key: string, fallback: string): string {
    return te(key) ? t(key) : fallback
  }

  return { lom, humanize, translate }
}
