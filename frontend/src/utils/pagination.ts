/**
 * unwrapResults — normalize a list endpoint response into a plain array,
 * whether DRF returned a paginated `{ results: [...] }` envelope or a bare
 * array. Replaces the ~35 copies of `res.data.results ?? res.data` and the
 * per-store `unwrapResults` helpers scattered across stores and views.
 */
export function unwrapResults<T>(data: unknown): T[] {
  if (!data) return []
  if (Array.isArray(data)) return data as T[]
  const results = (data as { results?: unknown }).results
  if (Array.isArray(results)) return results as T[]
  return []
}

/** Total item count from a DRF paginated envelope, else the array length. */
export function resultCount(data: unknown): number {
  if (!data) return 0
  if (Array.isArray(data)) return data.length
  const envelope = data as { count?: number; results?: unknown[] }
  if (typeof envelope.count === 'number') return envelope.count
  if (Array.isArray(envelope.results)) return envelope.results.length
  return 0
}
