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
