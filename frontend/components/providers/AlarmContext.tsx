'use client'

import { createContext, useContext, useEffect, useRef, useState } from 'react'

export interface Alarm {
  alarm_name: string
  source_name: string
  alarm_at: string
  elapsed_seconds: number
  escalated: boolean
  slack_message_ts: string
  channel_id: string
}

interface AlarmContextValue {
  alarms: Alarm[]
  count: number
  loading: boolean
  refresh: () => void
}

const AlarmContext = createContext<AlarmContextValue>({
  alarms: [],
  count: 0,
  loading: true,
  refresh: () => {},
})

export function useAlarms() {
  return useContext(AlarmContext)
}

const POLL_INTERVAL_MS = 30_000

export function AlarmProvider({ children }: { children: React.ReactNode }) {
  const [alarms, setAlarms] = useState<Alarm[]>([])
  const [loading, setLoading] = useState(true)
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const fetchAlarms = async () => {
    try {
      const res = await fetch('/api/alarms', { cache: 'no-store' })
      if (res.ok) {
        const data = await res.json()
        setAlarms(Array.isArray(data) ? data : [])
      }
    } catch {
      // Keep stale data on network error
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchAlarms()
    timerRef.current = setInterval(fetchAlarms, POLL_INTERVAL_MS)
    return () => {
      if (timerRef.current) clearInterval(timerRef.current)
    }
  }, [])

  return (
    <AlarmContext.Provider
      value={{ alarms, count: alarms.length, loading, refresh: fetchAlarms }}
    >
      {children}
    </AlarmContext.Provider>
  )
}
