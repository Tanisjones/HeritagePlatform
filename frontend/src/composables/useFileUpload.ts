import { ref } from 'vue'
import api from '@/services/api'

/**
 * useFileUpload — the XHR-with-progress media uploader, extracted from
 * ContributionForm (which needed a live progress bar + cancel) and reused by
 * ResourceEditView. Uses XMLHttpRequest rather than axios because we need
 * `upload.onprogress`, which fetch/axios don't expose for request bodies.
 *
 *   const { uploading, progress, uploadFile, abort } = useFileUpload()
 *   const mediaId = await uploadFile(file, 'image')
 *
 * POSTs `multipart/form-data` { file, file_type } to `/media/` and resolves the
 * created media id. Rejects with an axios-shaped `{ response: { status, data } }`
 * (so extractApiError/useAiError still work) or `{ code: 'ERR_CANCELED' }` on abort.
 */
export function useFileUpload() {
  const uploading = ref(false)
  const progress = ref(0)
  const xhrRef = ref<XMLHttpRequest | null>(null)

  function uploadFile(file: File, fileType: string): Promise<string> {
    return new Promise<string>((resolve, reject) => {
      const token = localStorage.getItem('token')
      const url = `${api.defaults.baseURL}/media/`
      const xhr = new XMLHttpRequest()
      xhrRef.value = xhr
      uploading.value = true
      progress.value = 0

      xhr.open('POST', url, true)
      xhr.responseType = 'json'
      xhr.timeout = 600000
      if (token) xhr.setRequestHeader('Authorization', `Bearer ${token}`)

      xhr.upload.onprogress = (event) => {
        if (!event.total) return
        progress.value = Math.round((event.loaded / event.total) * 100)
      }

      let settled = false
      const done = () => {
        uploading.value = false
        if (xhrRef.value === xhr) xhrRef.value = null
      }

      const finalize = () => {
        if (settled) return
        if (xhr.readyState !== XMLHttpRequest.DONE) return
        settled = true
        done()

        const status = xhr.status
        // With responseType='json' the browser parses the body for us; `response`
        // is null when the body wasn't valid JSON (e.g. an nginx 5xx HTML page).
        // We must NOT touch xhr.responseText here — reading it while
        // responseType='json' throws InvalidStateError. So fall back to null.
        const data = xhr.response ?? null

        if (status >= 200 && status < 300) {
          const id = (data as { id?: unknown })?.id
          if (typeof id === 'string' && id.length) {
            resolve(id)
          } else {
            reject({ response: { status, data } })
          }
          return
        }
        reject({ response: { status, data } })
      }

      xhr.onload = finalize
      xhr.onreadystatechange = finalize
      xhr.onerror = () => {
        if (settled) return
        settled = true
        done()
        reject({ message: 'Network error' })
      }
      xhr.ontimeout = () => {
        if (settled) return
        settled = true
        done()
        reject({ message: 'Upload timed out' })
      }
      xhr.onabort = () => {
        if (settled) return
        settled = true
        done()
        reject({ code: 'ERR_CANCELED' })
      }

      const formData = new FormData()
      formData.append('file', file)
      formData.append('file_type', fileType)
      xhr.send(formData)
    })
  }

  function abort() {
    xhrRef.value?.abort()
  }

  return { uploading, progress, uploadFile, abort }
}
