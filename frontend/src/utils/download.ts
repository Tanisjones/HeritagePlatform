/**
 * Trigger a browser download from a Blob response (e.g. an axios blob).
 * Shared by the SCORM/route package exports and the GPX/KML route exports.
 */
export function saveBlob(data: Blob, filename: string): void {
  const url = window.URL.createObjectURL(data)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  window.URL.revokeObjectURL(url)
}

/**
 * Extract a human-readable error message from a failed blob request. When the
 * server returns an error as a Blob (responseType: 'blob'), the body must be
 * read as text; otherwise fall back to the provided default.
 */
export async function readBlobError(e: any, fallback: string): Promise<string> {
  try {
    if (e?.response?.data instanceof Blob) {
      const text = await (e.response.data as Blob).text()
      return text || fallback
    }
  } catch {
    /* keep fallback */
  }
  return fallback
}

/** Filesystem-safe slug for a download filename. */
export function slugifyFilename(value: string, fallback = 'download'): string {
  const slug = (value || '')
    .replace(/[^a-zA-Z0-9._-]+/g, '-')
    .replace(/-+/g, '-')
    .replace(/^[-.]+|[-.]+$/g, '')
  return slug || fallback
}
