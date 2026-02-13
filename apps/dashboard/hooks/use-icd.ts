/**
 * Hook para obtener datos del ICD
 */

import { useEffect, useState } from 'react'
import { api, ICDResponse } from '@/lib/api'

export function useICD() {
  const [icd, setIcd] = useState<ICDResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<Error | null>(null)

  useEffect(() => {
    async function fetchICD() {
      try {
        setLoading(true)
        const data = await api.getTodayICD()
        setIcd(data)
        setError(null)
      } catch (err) {
        setError(err as Error)
      } finally {
        setLoading(false)
      }
    }

    fetchICD()
    // Refrescar cada 5 minutos
    const interval = setInterval(fetchICD, 5 * 60 * 1000)
    return () => clearInterval(interval)
  }, [])

  return { icd, loading, error, refetch: () => api.getTodayICD().then(setIcd) }
}
