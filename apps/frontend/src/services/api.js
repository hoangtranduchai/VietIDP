/**
 * VietIDP API Service Layer
 * Centralized Axios instance + all API functions
 */
import axios from 'axios'
import { toast } from 'react-toastify'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

const api = axios.create({
  baseURL: API_BASE,
  timeout: 120000, // 2 min for heavy pipeline
  headers: { 'Content-Type': 'application/json' },
})

// ── Response interceptor: centralized error handling ─────────
api.interceptors.response.use(
  (res) => res,
  (err) => {
    const msg = err.response?.data?.detail
      || err.response?.data?.error
      || err.message
      || 'Unknown error'

    // Don't toast on cancelled requests or background health checks
    if (!axios.isCancel(err) && !err.config?.url?.includes('/health')) {
      toast.error(msg, { toastId: msg.slice(0, 30) })
    }
    return Promise.reject(err)
  }
)

// ═══════════════════════════════════════════════════════════════
// Document Processing
// ═══════════════════════════════════════════════════════════════

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

// ═══════════════════════════════════════════════════════════════
// Document CRUD
// ═══════════════════════════════════════════════════════════════

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

// ═══════════════════════════════════════════════════════════════
// Export
// ═══════════════════════════════════════════════════════════════

export function getExportUrl(id, format = 'json') {
  return `${API_BASE}/api/export/${id}?format=${format}`
}

// ═══════════════════════════════════════════════════════════════
// Chat
// ═══════════════════════════════════════════════════════════════

export async function chatWithDocument(question, documentId, context) {
  const res = await api.post('/api/chat', {
    question,
    document_id: documentId || undefined,
    context: context || undefined,
  })
  return res.data
}

// ═══════════════════════════════════════════════════════════════
// System
// ═══════════════════════════════════════════════════════════════

export async function healthCheck() {
  const res = await api.get('/api/health')
  return res.data
}

export default api
