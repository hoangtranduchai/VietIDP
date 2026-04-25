import { useState, useCallback } from 'react'

/**
 * Generic async API hook
 * Manages loading / data / error lifecycle for any API call
 *
 * Usage:
 *   const { data, loading, error, execute } = useApi(api.getDocuments)
 *   execute(0, 50) // calls api.getDocuments(0, 50)
 */
export function useApi(apiFn) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const execute = useCallback(async (...args) => {
    setLoading(true)
    setError(null)
    try {
      const result = await apiFn(...args)
      setData(result)
      return result
    } catch (err) {
      const msg = err.response?.data?.detail || err.message || 'Error'
      setError(msg)
      throw err
    } finally {
      setLoading(false)
    }
  }, [apiFn])

  const reset = useCallback(() => {
    setData(null)
    setError(null)
    setLoading(false)
  }, [])

  return { data, loading, error, execute, reset }
}
