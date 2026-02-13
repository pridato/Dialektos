/**
 * Hook para obtener datos biométricos
 */

import { useEffect, useState } from 'react'
import { api, BiometricData, RecentBiometric } from '@/lib/api'

export function useTodayBiometrics() {
  const [biometrics, setBiometrics] = useState<BiometricData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<Error | null>(null)

  useEffect(() => {
    async function fetchBiometrics() {
      try {
        setLoading(true)
        const data = await api.getTodayBiometrics()
        setBiometrics(data)
        setError(null)
      } catch (err) {
        setError(err as Error)
      } finally {
        setLoading(false)
      }
    }

    fetchBiometrics()
  }, [])

  return { biometrics, loading, error }
}

export function useRecentBiometrics(days: number = 14) {
  const [biometrics, setBiometrics] = useState<RecentBiometric[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<Error | null>(null)

  useEffect(() => {
    async function fetchBiometrics() {
      try {
        setLoading(true)
        const data = await api.getRecentBiometrics(days)
        setBiometrics(data)
        setError(null)
      } catch (err) {
        setError(err as Error)
      } finally {
        setLoading(false)
      }
    }

    fetchBiometrics()
  }, [days])

  return { biometrics, loading, error }
}
