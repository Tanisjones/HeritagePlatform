/**
 * Types for the AI-economy dashboard (G.5), mirroring the aggregation endpoints
 * in backend/apps/ai_services/usage_views.py. Monetary values arrive as strings
 * (Decimal precision preserved over JSON) — parse with Number() at the edge.
 */

/** One grouped row from /ai/usage/summary/. `key` is the group label. */
export interface AiUsageSummaryRow {
  key: string
  calls: number
  input_tokens: number
  output_tokens: number
  total_tokens: number
  /** USD, as a decimal string (e.g. "0.001234"). */
  estimated_cost_usd: string
}

export type AiUsageGroupBy = 'operation' | 'provider' | 'model' | 'user' | 'day'

/** Window-wide totals; `error_calls` is the true non-ok count over the period. */
export interface AiUsageTotals extends Omit<AiUsageSummaryRow, 'key'> {
  error_calls?: number
}

export interface AiUsageSummaryResponse {
  group_by: AiUsageGroupBy
  since: string
  until: string
  totals: AiUsageTotals
  rows: AiUsageSummaryRow[]
}

/** One daily bucket from /ai/usage/timeseries/. */
export interface AiUsageTimeseriesPoint {
  date: string
  calls: number
  total_tokens: number
  estimated_cost_usd: string
}

export interface AiUsageTimeseriesResponse {
  since: string
  until: string
  points: AiUsageTimeseriesPoint[]
}

/** One raw row from /ai/usage/recent/ (audit table). */
export interface AiUsageRecord {
  id: string
  created_at: string
  user_email: string | null
  operation: string
  provider: string
  model: string
  input_tokens: number | null
  output_tokens: number | null
  total_tokens: number | null
  estimated_cost_usd: string | null
  duration_ms: number | null
  status: 'ok' | 'error' | 'rate_limited'
  error_type: string
}

export interface AiUsageRecentResponse {
  count: number
  results: AiUsageRecord[]
}

/** Common query params accepted by all three endpoints. */
export interface AiUsageQuery {
  since?: string
  until?: string
  group_by?: AiUsageGroupBy
  limit?: number
}
