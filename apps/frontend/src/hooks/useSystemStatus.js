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
      } catch (err) {
        if (mounted) setStatus('inactive')
      }
    }

    // Initial check
    check()

    // Poll every 5 seconds
    intervalId = setInterval(check, 5000)

    return () => {
      mounted = false
      clearInterval(intervalId)
    }
  }, [])

  return status
}
