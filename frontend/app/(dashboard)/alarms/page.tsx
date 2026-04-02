'use client'

import { useEffect, useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { useAlarms, type Alarm } from '@/components/providers/AlarmContext'

// ─── helpers ────────────────────────────────────────────────────────────────

function formatElapsed(seconds: number): string {
  if (seconds < 60) return `${seconds}d`
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ${seconds % 60}d`
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  return `${h}j ${m}m`
}

function ElapsedBar({ seconds, escalated }: { seconds: number; escalated: boolean }) {
  // cap at 60 min for bar width
  const pct = Math.min((seconds / 3600) * 100, 100)
  const color = escalated
    ? 'bg-red-500'
    : seconds > 1800
    ? 'bg-orange-400'
    : 'bg-yellow-400'
  return (
    <div className="h-1 w-full rounded-full bg-muted overflow-hidden">
      <div className={`h-full rounded-full transition-all ${color}`} style={{ width: `${pct}%` }} />
    </div>
  )
}

function StatusBadge({ alarm }: { alarm: Alarm }) {
  if (alarm.escalated)
    return (
      <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400">
        Escalated
      </span>
    )
  if (alarm.elapsed_seconds > 1800)
    return (
      <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400">
        Overdue
      </span>
    )
  return (
    <span className="text-[10px] font-semibold px-2 py-0.5 rounded-full bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400">
      Active
    </span>
  )
}

// ─── Resolve dialog (inline, no modal lib needed) ────────────────────────────

function ResolveForm({
  alarm,
  onResolved,
}: {
  alarm: Alarm
  onResolved: () => void
}) {
  const [open, setOpen] = useState(false)
  const [notes, setNotes] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const submit = async () => {
    setLoading(true)
    setError(null)
    try {
      const params = notes ? `?notes=${encodeURIComponent(notes)}` : ''
      const res = await fetch(
        `/api/alarms/${encodeURIComponent(alarm.alarm_name)}/resolve${params}`,
        { method: 'POST' },
      )
      if (res.ok) {
        setOpen(false)
        setNotes('')
        onResolved()
      } else {
        const body = await res.json()
        setError(body.detail ?? 'Gagal resolve')
      }
    } catch {
      setError('Terjadi kesalahan')
    } finally {
      setLoading(false)
    }
  }

  if (!open) {
    return (
      <Button size="sm" variant="outline" className="h-7 text-xs" onClick={() => setOpen(true)}>
        Resolve
      </Button>
    )
  }

  return (
    <div className="flex flex-col gap-2 mt-2">
      {error && <p className="text-xs text-destructive">{error}</p>}
      <Input
        placeholder="Catatan (opsional)"
        value={notes}
        onChange={e => setNotes(e.target.value)}
        className="h-7 text-xs"
        onKeyDown={e => e.key === 'Enter' && submit()}
      />
      <div className="flex gap-2">
        <Button size="sm" className="h-7 text-xs" onClick={submit} disabled={loading}>
          {loading ? 'Resolving...' : 'Konfirmasi'}
        </Button>
        <Button size="sm" variant="ghost" className="h-7 text-xs" onClick={() => setOpen(false)}>
          Batal
        </Button>
      </div>
    </div>
  )
}

// ─── Stats card ──────────────────────────────────────────────────────────────

function StatsPanel() {
  const [stats, setStats] = useState<any>(null)
  const [health, setHealth] = useState<any>(null)

  useEffect(() => {
    fetch('/api/alarms/stats').then(r => r.ok ? r.json() : null).then(setStats)
    fetch('/api/alarms/health').then(r => r.ok ? r.json() : null).then(setHealth)
  }, [])

  return (
    <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
      <div className="rounded-lg border bg-card p-4">
        <p className="text-xs text-muted-foreground">Status Forwarder</p>
        <p className={`text-sm font-semibold mt-1 ${health?.scheduler_running ? 'text-green-500' : 'text-red-500'}`}>
          {health == null ? '—' : health.scheduler_running ? 'Running' : 'Stopped'}
        </p>
      </div>
      <div className="rounded-lg border bg-card p-4">
        <p className="text-xs text-muted-foreground">Last Poll</p>
        <p className="text-sm font-semibold mt-1">
          {health?.last_poll
            ? new Date(health.last_poll).toLocaleTimeString('id-ID')
            : '—'}
        </p>
      </div>
      <div className="rounded-lg border bg-card p-4">
        <p className="text-xs text-muted-foreground">Email Diproses</p>
        <p className="text-sm font-semibold mt-1">
          {stats?.emails?.total_processed ?? '—'}
        </p>
      </div>
      <div className="rounded-lg border bg-card p-4">
        <p className="text-xs text-muted-foreground">Email Dilewati</p>
        <p className="text-sm font-semibold mt-1">
          {stats?.emails?.total_skipped ?? '—'}
        </p>
      </div>
    </div>
  )
}

// ─── Main page ───────────────────────────────────────────────────────────────

export default function AlarmsPage() {
  const { alarms, count, loading, refresh } = useAlarms()

  return (
    <div className="space-y-6 p-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Active Alarms</h1>
          <p className="text-sm text-muted-foreground mt-1">
            CloudWatch alarms dari gmail-alert-forwarder · auto-refresh setiap 30 detik
          </p>
        </div>
        <Button size="sm" variant="outline" onClick={refresh}>
          Refresh
        </Button>
      </div>

      <StatsPanel />

      {/* Alarm list */}
      <div className="rounded-lg border bg-card">
        <div className="px-5 py-3 border-b flex items-center justify-between">
          <h2 className="font-medium text-sm">
            Alarm Aktif
            {count > 0 && (
              <span className="ml-2 rounded-full bg-red-500 px-2 py-0.5 text-[10px] font-bold text-white">
                {count}
              </span>
            )}
          </h2>
        </div>

        {loading ? (
          <p className="px-5 py-6 text-sm text-muted-foreground">Memuat...</p>
        ) : alarms.length === 0 ? (
          <div className="px-5 py-8 text-center">
            <p className="text-sm font-medium text-green-500">Tidak ada alarm aktif</p>
            <p className="text-xs text-muted-foreground mt-1">Semua sistem normal</p>
          </div>
        ) : (
          <div className="divide-y">
            {alarms.map(alarm => (
              <div key={alarm.alarm_name} className="px-5 py-4 space-y-2">
                <div className="flex items-start justify-between gap-4">
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2 flex-wrap">
                      <p className="text-sm font-mono font-medium truncate">{alarm.alarm_name}</p>
                      <StatusBadge alarm={alarm} />
                    </div>
                    <p className="text-xs text-muted-foreground mt-0.5">
                      {alarm.source_name} · alarm sejak {alarm.alarm_at} ·{' '}
                      <span className={alarm.escalated ? 'text-red-500 font-medium' : ''}>
                        {formatElapsed(alarm.elapsed_seconds)}
                      </span>
                    </p>
                  </div>
                  <ResolveForm alarm={alarm} onResolved={refresh} />
                </div>
                <ElapsedBar seconds={alarm.elapsed_seconds} escalated={alarm.escalated} />
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
