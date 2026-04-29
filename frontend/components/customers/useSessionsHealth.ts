import { useCallback, useEffect, useState } from 'react'
import type { SessionsHealth, ProfileHealth } from '@/lib/types/api'

const CACHE_KEY = 'customers:sessions-health:v1'

interface UseSessionsHealthReturn {
  healthMap: Record<string, ProfileHealth>
  healthLoading: boolean
  healthError: boolean
  lastCheckedAt: number | null
  refresh: () => Promise<void>
}

export function useSessionsHealth(): UseSessionsHealthReturn {
  const [sessionsHealth, setSessionsHealth] = useState<SessionsHealth | null>(null)
  const [healthLoading, setHealthLoading] = useState(false)
  const [healthError, setHealthError] = useState(false)
  const [lastCheckedAt, setLastCheckedAt] = useState<number | null>(null)

  const refresh = useCallback(async () => {
    setHealthLoading(true)
    setHealthError(false)
    try {
      const r = await fetch('/api/sessions-health')
      if (!r.ok) throw new Error('health check failed')
      const data = (await r.json()) as SessionsHealth
      const checkedAt = Date.now()
      setSessionsHealth(data)
      setLastCheckedAt(checkedAt)
      window.sessionStorage.setItem(CACHE_KEY, JSON.stringify({ checkedAt, data }))
    } catch {
      setHealthError(true)
    } finally {
      setHealthLoading(false)
    }
  }, [])

  useEffect(() => {
    const raw = window.sessionStorage.getItem(CACHE_KEY)
    if (!raw) return
    try {
      const parsed = JSON.parse(raw) as { checkedAt?: number; data?: SessionsHealth }
      if (parsed?.data) {
        setSessionsHealth(parsed.data)
        setLastCheckedAt(parsed.checkedAt ?? null)
      }
    } catch {
      window.sessionStorage.removeItem(CACHE_KEY)
    }
  }, [])

  const healthMap: Record<string, ProfileHealth> = {}
  if (sessionsHealth?.profiles) {
    for (const p of sessionsHealth.profiles) healthMap[p.profile_name] = p
  }

  return { healthMap, healthLoading, healthError, lastCheckedAt, refresh }
}
