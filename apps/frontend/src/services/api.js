/**
 * VietIDP API Service Layer
 * Centralized Axios instance + all API functions
 */
import axios from 'axios'
import { toast } from 'react-toastify'

const configuredBase = (import.meta.env.VITE_API_URL || '').trim()
const API_BASE = configuredBase.replace(/\/$/, '')
// Vite env vars are bundled into the browser, so this header is only for local/dev convenience.
const BROWSER_API_KEY = (import.meta.env.VITE_API_KEY || '').trim()

const api = axios.create({
  baseURL: API_BASE,
  timeout: 120000,
  headers: {
    'Content-Type': 'application/json',
    ...(BROWSER_API_KEY ? { 'X-API-Key': BROWSER_API_KEY } : {}),
  },
})

function getApiPath(path) {
  return `${API_BASE}${path}`
}

api.interceptors.response.use(
  (res) => res,
  (err) => {
    const msg = err.response?.data?.detail
      || err.response?.data?.error
      || err.message
      || 'Unknown error'

    if (!axios.isCancel(err) && !err.config?.url?.includes('/health') && !err.config?.skipToast) {
      toast.error(msg, { toastId: msg.slice(0, 30) })
    }
    return Promise.reject(err)
  }
)

export async function processDocument(file, onProgress) {
  const formData = new FormData()
  formData.append('file', file)
  const res = await api.post('/api/process_document?async_mode=true', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: onProgress,
  })
  return res.data
}

export async function getTaskStatus(taskId) {
  const res = await api.get(`/api/task_status/${taskId}`)
  return res.data
}

export async function getDocuments(skip = 0, limit = 50, status) {
  const params = { skip, limit }
  if (status) params.status = status
  const res = await api.get('/api/documents', { params })
  return res.data
}

export async function getDocument(id) {
  const res = await api.get(`/api/documents/${id}`)
  return res.data
}

export async function updateDocument(id, data) {
  const res = await api.put(`/api/documents/${id}`, data)
  toast.success('Saved successfully!')
  return res.data
}

export async function deleteDocument(id) {
  const res = await api.delete(`/api/documents/${id}`)
  return res.data
}

export async function downloadExport(id, format = 'json') {
  const res = await api.get(`/api/export/${id}`, {
    params: { format },
    responseType: 'blob',
  })

  const contentType = res.headers['content-type'] || (format === 'csv' ? 'text/csv' : 'application/json')
  const blob = new Blob([res.data], { type: contentType })
  const objectUrl = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = objectUrl
  link.download = `doc_${id}.${format}`
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(objectUrl)
}

export async function getDocumentPreviewBlobUrl(id, page = 1) {
  const res = await api.get(`/api/documents/${id}/preview`, {
    params: { page },
    responseType: 'blob',
  })
  return URL.createObjectURL(res.data)
}

export function getDocumentPreviewPath(id, page = 1) {
  return getApiPath(`/api/documents/${id}/preview?page=${page}`)
}

export async function chatWithDocument(question, documentId, context) {
  const res = await api.post('/api/chat', {
    question,
    document_id: documentId || undefined,
    context: context || undefined,
  })
  return res.data
}

export async function healthCheck() {
  try {
    const res = await api.get('/api/health', { skipToast: true })
    return res.data
  } catch (err) {
    throw err
  }
}

export default api
