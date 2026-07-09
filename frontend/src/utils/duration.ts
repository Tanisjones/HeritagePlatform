/**
 * ISO-8601 duration helpers, kept in one place so the LOM editor's validation,
 * the /learn duration filter, and any future consumer agree on one grammar.
 *
 * The grammar mirrors the backend validator (apps/education/models.py
 * `validate_iso8601_duration`): P[nY][nM][nW][nD][T[nH][nM][nS]], at least one
 * component, no bare "P"/"PT".
 */

// Full ISO-8601 duration (years/months/weeks/days + time). Matches the backend.
export const ISO8601_DURATION_RE =
  /^P(?!$)(\d+Y)?(\d+M)?(\d+W)?(\d+D)?(T(?!$)(\d+H)?(\d+M)?(\d+S)?)?$/;

export function isValidIso8601Duration(value: string | null | undefined): boolean {
  if (!value) return true; // empty is allowed (optional field)
  return ISO8601_DURATION_RE.test(value);
}

/**
 * Convert an ISO-8601 duration to minutes. Returns null only when the value is
 * genuinely unparseable — a real zero-length duration ("PT0S") returns 0, not
 * null, so callers can distinguish "no duration" from "zero".
 *
 * Calendar components are approximated (year = 365 d, month = 30 d, week = 7 d)
 * which is fine for coarse learning-time bucketing.
 */
export function iso8601ToMinutes(value: string | null | undefined): number | null {
  if (!value) return null;
  const m = value.match(ISO8601_DURATION_RE);
  if (!m) return null;
  // Groups: 1=Y 2=M(months) 3=W 4=D 5=T… 6=H 7=M(minutes) 8=S
  const num = (g: string | undefined) => (g ? parseInt(g, 10) : 0);
  const years = num(m[1]);
  const months = num(m[2]);
  const weeks = num(m[3]);
  const days = num(m[4]);
  const hours = num(m[6]);
  const minutes = num(m[7]);
  const seconds = num(m[8]);
  return (
    years * 365 * 24 * 60 +
    months * 30 * 24 * 60 +
    weeks * 7 * 24 * 60 +
    days * 24 * 60 +
    hours * 60 +
    minutes +
    seconds / 60
  );
}

/**
 * Human-readable rendering of an ISO-8601 duration (A.2): "PT1H" → "1 h",
 * "PT1H30M" → "1 h 30 min", "PT45M" → "45 min", "P2D" → "2 d". Returns null
 * when the value is empty or unparseable so callers can fall back (or hide).
 * Unit abbreviations (min/h/d) read the same in es and en, so no i18n needed.
 */
export function formatIsoDuration(value: string | null | undefined): string | null {
  const total = iso8601ToMinutes(value);
  if (total === null) return null;
  const minutes = Math.round(total);
  if (minutes < 1) return `${total > 0 ? '<1' : '0'} min`;
  const DAY = 24 * 60;
  if (minutes >= DAY) {
    const days = Math.floor(minutes / DAY);
    const hours = Math.round((minutes % DAY) / 60);
    return hours ? `${days} d ${hours} h` : `${days} d`;
  }
  const hours = Math.floor(minutes / 60);
  const rest = minutes % 60;
  if (!hours) return `${rest} min`;
  return rest ? `${hours} h ${rest} min` : `${hours} h`;
}

/**
 * True when a value is a syntactically valid duration whose only component is a
 * date-part "M" (months) with no time part — the classic "P30M meant 30 minutes"
 * footgun. Callers can warn the user to use "PT30M" instead.
 */
export function looksLikeMonthsNotMinutes(value: string | null | undefined): boolean {
  if (!value) return false;
  return /^P\d+M$/.test(value);
}
