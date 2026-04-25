import { useState, useEffect, useCallback } from 'react'
import { getDocuments, deleteDocument } from '../services/api'

/**
 * Hook for document list operations
 * Provides: documents, total, loading, refresh, deleteDoc
 */
export function useDocuments(limit = 50) {
  const [documents, setDocuments] = useState([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const refresh = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await getDocuments(0, limit)
      setDocuments(res.documents || [])
      setTotal(res.total || 0)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [limit])

  const deleteDoc = useCallback(async (id) => {
    await deleteDocument(id)
    setDocuments(prev => prev.filter(d => d.id !== id))
    setTotal(prev => prev - 1)
  }, [])

  useEffect(() => { refresh() }, [refresh])

  return { documents, total, loading, error, refresh, deleteDoc }
}
