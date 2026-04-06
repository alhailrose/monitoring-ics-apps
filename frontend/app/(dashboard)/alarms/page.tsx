'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Checkbox } from '@/components/ui/checkbox'
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

// ─── Resolve dialog ──────────────────────────────────────────────────────────

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

// ─── Single verify button ─────────────────────────────────────────────────────

type VerifyResult = {
  mapped_accounts: number
  counts: Record<string, number>
  alarm_states?: Record<string, string>
  auto_resolved?: string[]
  check_run_id?: string | null
}

type VerifyState = {
  loading: boolean
  error?: string
  result?: VerifyResult
}

function VerifyNowButton({ alarmName, onAutoResolved }: { alarmName: string; onAutoResolved?: () => void }) {
  const [state, setState] = useState<VerifyState>({ loading: false })

  const verifyNow = async () => {
    setState({ loading: true })
    try {
      const res = await fetch(`/api/alarms/${encodeURIComponent(alarmName)}/verify`, {
        method: 'POST',
      })
      const body = await res.json().catch(() => null)
      if (!res.ok) {
        setState({ loading: false, error: body?.detail ?? 'Gagal cek alarm' })
        return
      }
      const result: VerifyResult = {
        mapped_accounts: Number(body?.mapped_accounts ?? 0),
        counts: (body?.counts ?? {}) as Record<string, number>,
        alarm_states: body?.alarm_states ?? {},
        auto_resolved: body?.auto_resolved ?? [],
        check_run_id: body?.check_run_id ?? null,
      }
      setState({ loading: false, result })
      if (result.auto_resolved && result.auto_resolved.length > 0) {
        onAutoResolved?.()
      }
    } catch {
      setState({ loading: false, error: 'Terjadi kesalahan jaringan' })
    }
  }

  const counts = state.result?.counts ?? {}
  const alarmState = state.result?.alarm_states?.[alarmName]
  const autoResolved = state.result?.auto_resolved ?? []
  const summaryParts = [
    counts.ALARM ? `${counts.ALARM} ALARM` : null,
    counts.OK ? `${counts.OK} OK` : null,
    counts.ERROR ? `${counts.ERROR} ERROR` : null,
    counts.NO_DATA ? `${counts.NO_DATA} NO_DATA` : null,
  ].filter(Boolean)

  return (
    <div className="flex flex-col items-end gap-1.5">
      <Button size="sm" variant="secondary" className="h-7 text-xs" onClick={verifyNow} disabled={state.loading}>
        {state.loading ? 'Mengecek...' : 'Cek Sekarang'}
      </Button>
      {state.error && <p className="text-[11px] text-destructive text-right max-w-72">{state.error}</p>}
      {state.result && (
        <div className="text-[11px] text-right max-w-72 space-y-0.5">
          <p className={`${alarmState === 'OK' ? 'text-green-500' : alarmState === 'ALARM' ? 'text-red-500' : 'text-muted-foreground'}`}>
            {alarmState ? `CloudWatch: ${alarmState}` : (summaryParts.length > 0 ? summaryParts.join(' · ') : 'Tidak ada hasil')}
            {state.result.mapped_accounts > 0 ? ` · ${state.result.mapped_accounts} akun` : ''}
          </p>
          {autoResolved.length > 0 && (
            <p className="text-green-500 font-medium">✓ Auto-resolved</p>
          )}
          {state.result.check_run_id && (
            <Link href={`/history/${state.result.check_run_id}`} className="text-sky-400 hover:text-sky-300 underline">
              Lihat detail run
            </Link>
          )}
        </div>
      )}
    </div>
  )
}

// ─── Batch verify bar ────────────────────────────────────────────────────────

type BatchVerifyState = {
  loading: boolean
  error?: string
  result?: {
    verified: string[]
    mapped_accounts: number
    alarm_states: Record<string, string>
    auto_resolved: string[]
    check_run_id?: string | null
  }
}

function BatchVerifyBar({
  selected,
  onDone,
}: {
  selected: string[]
  onDone: () => void
}) {
  const [state, setState] = useState<BatchVerifyState>({ loading: false })

  const runBatch = async () => {
    setState({ loading: true, error: undefined, result: undefined })
    try {
      const res = await fetch('/api/alarms/verify-batch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ alarm_names: selected }),
      })
      const body = await res.json().catch(() => null)
      if (!res.ok) {
        setState({ loading: false, error: body?.detail ?? 'Gagal verifikasi batch' })
        return
      }
      setState({
        loading: false,
        result: {
          verified: body?.verified ?? [],
          mapped_accounts: Number(body?.mapped_accounts ?? 0),
          alarm_states: body?.alarm_states ?? {},
          auto_resolved: body?.auto_resolved ?? [],
          check_run_id: body?.check_run_id ?? null,
        },
      })
      if ((body?.auto_resolved ?? []).length > 0) onDone()
    } catch {
      setState({ loading: false, error: 'Terjadi kesalahan jaringan' })
    }
  }

  const states = state.result?.alarm_states ?? {}
  const autoResolved = state.result?.auto_resolved ?? []
  const alarmCount = selected.length

  if (alarmCount === 0) return null

  return (
    <div className="flex flex-col gap-2 rounded-lg border border-yellow-500/30 bg-yellow-500/5 px-4 py-3">
      <div className="flex items-center justify-between gap-4">
        <p className="text-sm text-muted-foreground">
          <span className="font-medium text-foreground">{alarmCount}</span> alarm dipilih
        </p>
        <Button size="sm" onClick={runBatch} disabled={state.loading} className="h-7 text-xs">
          {state.loading ? 'Mengecek...' : `Cek Semua (${alarmCount})`}
        </Button>
      </div>

      {state.error && <p className="text-xs text-destructive">{state.error}</p>}

      {state.result && (
        <div className="space-y-1">
          <div className="flex flex-wrap gap-2">
            {Object.entries(states).map(([name, st]) => (
              <span
                key={name}
                className={`text-[11px] rounded px-2 py-0.5 font-mono ${
                  st === 'OK'
                    ? 'bg-green-500/15 text-green-500'
                    : st === 'ALARM'
                    ? 'bg-red-500/15 text-red-500'
                    : st === 'NOT_FOUND'
                    ? 'bg-red-500/15 text-red-400'
                    : 'bg-muted text-muted-foreground'
                }`}
              >
                {name}: {st}
              </span>
            ))}
          </div>
          {autoResolved.length > 0 && (
            <p className="text-[11px] text-green-500 font-medium">
              ✓ Auto-resolved: {autoResolved.join(', ')}
            </p>
          )}
          {state.result.check_run_id && (
            <Link
              href={`/history/${state.result.check_run_id}`}
              className="text-[11px] text-sky-400 hover:text-sky-300 underline"
            >
              Lihat detail run
            </Link>
          )}
        </div>
      )}
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
  const [selected, setSelected] = useState<Set<string>>(new Set())

  const toggleSelect = (name: string) => {
    setSelected(prev => {
      const next = new Set(prev)
      if (next.has(name)) next.delete(name)
      else next.add(name)
      return next
    })
  }

  const toggleSelectAll = () => {
    if (selected.size === alarms.length) {
      setSelected(new Set())
    } else {
      setSelected(new Set(alarms.map(a => a.alarm_name)))
    }
  }

  // Clear selection when alarm list changes (e.g., after refresh)
  useEffect(() => {
    setSelected(prev => {
      const activeNames = new Set(alarms.map(a => a.alarm_name))
      const next = new Set([...prev].filter(n => activeNames.has(n)))
      return next.size === prev.size ? prev : next
    })
  }, [alarms])

  const selectedList = [...selected]

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

      {/* Batch verify bar */}
      {selectedList.length > 0 && (
        <BatchVerifyBar
          selected={selectedList}
          onDone={() => {
            setSelected(new Set())
            setTimeout(refresh, 1500)
          }}
        />
      )}

      {/* Alarm list */}
      <div className="rounded-lg border bg-card">
        <div className="px-5 py-3 border-b flex items-center justify-between">
          <div className="flex items-center gap-3">
            {alarms.length > 0 && (
              <Checkbox
                checked={selected.size === alarms.length && alarms.length > 0}
                onCheckedChange={toggleSelectAll}
                aria-label="Pilih semua"
              />
            )}
            <h2 className="font-medium text-sm">
              Alarm Aktif
              {count > 0 && (
                <span className="ml-2 rounded-full bg-red-500 px-2 py-0.5 text-[10px] font-bold text-white">
                  {count}
                </span>
              )}
            </h2>
          </div>
          {selected.size > 0 && (
            <p className="text-xs text-muted-foreground">{selected.size} dipilih</p>
          )}
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
              <div
                key={alarm.alarm_name}
                className={`px-5 py-4 space-y-2 transition-colors ${selected.has(alarm.alarm_name) ? 'bg-muted/40' : ''}`}
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="flex items-start gap-3 min-w-0 flex-1">
                    <Checkbox
                      checked={selected.has(alarm.alarm_name)}
                      onCheckedChange={() => toggleSelect(alarm.alarm_name)}
                      className="mt-0.5 shrink-0"
                      aria-label={`Pilih ${alarm.alarm_name}`}
                    />
                    <div className="min-w-0">
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
                  </div>
                  <div className="flex items-start gap-2">
                    <VerifyNowButton
                      alarmName={alarm.alarm_name}
                      onAutoResolved={() => setTimeout(refresh, 1500)}
                    />
                    <ResolveForm alarm={alarm} onResolved={refresh} />
                  </div>
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
