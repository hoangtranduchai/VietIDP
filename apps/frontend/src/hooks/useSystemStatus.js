import { useState, useEffect } from 'react'
import { healthCheck } from '../services/api'

export function useSystemStatus() {
  const [status, setStatus] = useState('active')

  useEffect(() => {
    let mounted = true
    let intervalId

    const check = async () => {
      try {
        await healthCheck()
        if (mounted) setStatus('active')
      } catch {
        if (mounted) setStatus('inactive')
      }
    }

    // Initial check
    check()

    // Poll every 30 seconds (status indicator doesn't need rapid updates)
    intervalId = setInterval(check, 30000)

    return () => {
      mounted = false
      clearInterval(intervalId)
    }
  }, [])

  return status
}
