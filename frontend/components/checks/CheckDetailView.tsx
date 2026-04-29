'use client'

import { Badge } from '@/components/ui/badge'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { cn, formatDateFull } from '@/lib/utils'

interface CheckDetailViewProps {
  checkName: string
  details: Record<string, unknown>
}

function statusBadge(status: string) {
  const s = status.toUpperCase()
  if (s === 'OK' || s === 'NORMAL') return <Badge variant="outline" className="bg-emerald-500/10 text-emerald-600 border-emerald-500/20">{s}</Badge>
  if (s === 'WARN' || s === 'WARNING' || s === 'PAST-WARN') return <Badge variant="outline" className="bg-amber-500/10 text-amber-600 border-amber-500/20">{s}</Badge>
  if (s === 'ERROR' || s === 'ALARM' || s === 'CRITICAL') return <Badge variant="outline" className="bg-red-500/10 text-red-600 border-red-500/20">{s}</Badge>
  if (s === 'DISABLED' || s === 'NO_DATA' || s === 'PARTIAL_DATA') return <Badge variant="outline" className="text-muted-foreground">{s}</Badge>
  return <Badge variant="outline">{s}</Badge>
}

function fmtPct(val: unknown): string {
  if (typeof val === 'number') return `${val.toFixed(2)}%`
  return '-'
}

function fmtBytes(val: unknown): string {
  if (typeof val !== 'number') return '-'
  if (val >= 1024 ** 3) return `${(val / 1024 ** 3).toFixed(2)} GB`
  if (val >= 1024 ** 2) return `${(val / 1024 ** 2).toFixed(2)} MB`
  if (val >= 1024)      return `${(val / 1024).toFixed(2)} KB`
  return `${Math.round(val)} B`
}

function fmtDollar(val: unknown): string {
  if (typeof val === 'number') return `$${val.toFixed(2)}`
  if (typeof val === 'string') return `$${parseFloat(val).toFixed(2)}`
  return '-'
}

// ─── Arbel (RDS/EC2) ─────────────────────────────────────────────────────────

interface ArbelMetric {
  avg?: number | null
  last?: number | null
  max?: number | null
  status?: string
  message?: string
}

interface ArbelInstanceData {
  instance_id?: string
  instance_name?: string
  metrics?: Record<string, ArbelMetric>
  disk_memory_alarms?: Array<{ alarm_name: string; current_state: string }>
}

function ArbelDetail({ details }: { details: Record<string, unknown> }) {
  const instances = (details.instances ?? {}) as Record<string, ArbelInstanceData>
  const extraSections = (details.extra_sections ?? []) as Array<Record<string, unknown>>
  const windowHours = details.window_hours as number | undefined
  const serviceType = (details.service_type as string) ?? 'rds'

  return (
    <div className="space-y-3">
      {windowHours && (
        <p className="text-[11px] text-muted-foreground">
          Window: {windowHours}h · Type: {serviceType.toUpperCase()}
        </p>
      )}
      <ArbelInstanceTable instances={instances} serviceType={serviceType} />
      {extraSections.map((section, idx) => {
        const sectionInstances = (section.instances ?? {}) as Record<string, ArbelInstanceData>
        const sectionName = (section.section_name as string) ?? `Section ${idx + 1}`
        const sectionType = (section.service_type as string) ?? 'rds'
        return (
          <div key={idx}>
            <p className="text-[11px] font-medium text-muted-foreground mb-1">{sectionName} ({sectionType.toUpperCase()})</p>
            <ArbelInstanceTable instances={sectionInstances} serviceType={sectionType} />
          </div>
        )
      })}
    </div>
  )
}

function ArbelInstanceTable({ instances, serviceType }: { instances: Record<string, ArbelInstanceData>; serviceType: string }) {
  const entries = Object.entries(instances)
  if (entries.length === 0) return <p className="text-[11px] text-muted-foreground italic">No instance data</p>

  // Collect all metric names across instances
  const metricNames = new Set<string>()
  for (const [, data] of entries) {
    for (const name of Object.keys(data.metrics ?? {})) {
      metricNames.add(name)
    }
  }
  const orderedMetrics = Array.from(metricNames)
  const detailMessages = entries.flatMap(([role, data]) => {
    const instName = data.instance_name || data.instance_id || role
    const metrics = data.metrics ?? {}
    return Object.values(metrics)
      .filter((info) => {
        const status = String(info.status ?? '').toLowerCase()
        return (status === 'warn' || status === 'past-warn' || status === 'alarm') && Boolean(info.message)
      })
      .map((info) => ({
        instName,
        message: String(info.message ?? '').trim(),
      }))
      .filter((row) => row.message.length > 0)
  })

  return (
    <div className="space-y-2">
      <div className="overflow-x-auto rounded-md border border-border/40">
      <Table>
        <TableHeader>
          <TableRow className="hover:bg-transparent">
            <TableHead>Instance</TableHead>
            {orderedMetrics.map((m) => (
              <TableHead key={m} className="text-right">{metricLabel(m)}</TableHead>
            ))}
            <TableHead className="text-center">Status</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {entries.map(([role, data]) => {
            const instName = data.instance_name || data.instance_id || role
            const metrics = data.metrics ?? {}
            const alarms = data.disk_memory_alarms ?? []
            const worstStatus = getWorstMetricStatus(metrics, alarms)

            return (
              <TableRow key={role}>
                <TableCell className="font-mono text-foreground">
                  {instName}
                  {data.instance_id && data.instance_id !== instName && (
                    <span className="block text-[10px] text-muted-foreground">{data.instance_id}</span>
                  )}
                </TableCell>
                {orderedMetrics.map((m) => {
                  const info = metrics[m]
                  if (!info) return <TableCell key={m} className="text-right text-muted-foreground">-</TableCell>
                  return (
                    <TableCell key={m} className={cn('text-right font-mono', metricCellColor(info.status))}>
                      {formatMetricValue(m, info)}
                    </TableCell>
                  )
                })}
                <TableCell className="text-center">{statusBadge(worstStatus)}</TableCell>
              </TableRow>
            )
          })}
        </TableBody>
      </Table>
      </div>
      {detailMessages.length > 0 && (
        <div className="rounded-md border border-border/60 bg-muted/20 p-2">
          <p className="text-[10px] font-semibold uppercase tracking-wide text-muted-foreground mb-1">Details</p>
          <div className="space-y-1">
            {detailMessages.map((item, index) => (
              <p key={`${item.instName}-${index}`} className="text-[11px] leading-relaxed text-foreground">
                <span className="font-medium">{item.instName}:</span> {item.message}
              </p>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

function metricLabel(name: string): string {
  const map: Record<string, string> = {
    CPUUtilization: 'CPU',
    ACUUtilization: 'ACU',
    FreeableMemory: 'Memory',
    FreeStorageSpace: 'Disk Free',
    DatabaseConnections: 'Connections',
    BufferCacheHitRatio: 'Buffer Cache',
    NetworkIn: 'Net In',
    NetworkOut: 'Net Out',
  }
  return map[name] ?? name
}

function formatMetricValue(name: string, info: ArbelMetric): string {
  const avg = info.avg
  const last = info.last

  if (name === 'FreeableMemory') {
    const val = avg ?? last
    return val != null ? fmtBytes(val) : '-'
  }
  if (name === 'FreeStorageSpace') {
    const val = last ?? avg
    return val != null ? fmtBytes(val) : '-'
  }
  if (name === 'DatabaseConnections' || name === 'ServerlessDatabaseCapacity') {
    const val = last ?? avg
    return val != null ? String(Math.round(val)) : '-'
  }
  if (name === 'BufferCacheHitRatio') {
    const val = avg ?? last
    return val != null ? fmtPct(val) : '-'
  }
  if (name === 'NetworkIn' || name === 'NetworkOut' ||
      name === 'NetworkReceiveThroughput' || name === 'NetworkTransmitThroughput') {
    const val = avg ?? last
    return val != null ? fmtBytes(val) : '-'
  }
  // CPU, ACU, and any remaining percent metrics
  const val = avg ?? last
  return val != null ? fmtPct(val) : '-'
}

function metricCellColor(status?: string): string {
  if (!status) return ''
  if (status === 'warn') return 'text-amber-600'
  if (status === 'past-warn') return 'text-amber-500'
  return ''
}

function getWorstMetricStatus(
  metrics: Record<string, ArbelMetric>,
  alarms: Array<{ alarm_name: string; current_state: string }>,
): string {
  const hasAlarm = alarms.some((a) => a.current_state === 'ALARM')
  if (hasAlarm) return 'ALARM'
  let worst = 'ok'
  for (const info of Object.values(metrics)) {
    if (info.status === 'warn') worst = 'warn'
    else if (info.status === 'past-warn' && worst === 'ok') worst = 'past-warn'
  }
  return worst
}

// ─── Utilization 3-Core ──────────────────────────────────────────────────────

function UtilizationDetail({ details }: { details: Record<string, unknown> }) {
  const instances = (details.instances ?? []) as Array<Record<string, unknown>>
  if (instances.length === 0) return <p className="text-[11px] text-muted-foreground italic">No instance data</p>

  return (
    <div className="overflow-x-auto rounded-md border border-border/40">
      <Table>
        <TableHeader>
          <TableRow className="hover:bg-transparent">
            <TableHead>Instance</TableHead>
            <TableHead className="text-right">CPU avg</TableHead>
            <TableHead className="text-right">CPU peak</TableHead>
            <TableHead className="text-right">MEM avg</TableHead>
            <TableHead className="text-right">MEM peak</TableHead>
            <TableHead className="text-right">Disk Free</TableHead>
            <TableHead className="text-center">Status</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {instances.map((row, i) => {
            const instanceId = String(row.instance_id ?? '')
            const name = (row.name as string) || instanceId || '-'
            const status = ((row.status as string) ?? 'NORMAL').toUpperCase()
            return (
              <TableRow key={i}>
                <TableCell className="font-mono text-foreground">
                  {name}
                  {instanceId && instanceId !== name && (
                    <span className="block text-[10px] text-muted-foreground">{instanceId}</span>
                  )}
                </TableCell>
                <TableCell className="text-right font-mono">{fmtPct(row.cpu_avg_12h)}</TableCell>
                <TableCell className="text-right font-mono">{fmtPct(row.cpu_peak_12h)}</TableCell>
                <TableCell className="text-right font-mono">{fmtPct(row.memory_avg_12h)}</TableCell>
                <TableCell className="text-right font-mono">{fmtPct(row.memory_peak_12h)}</TableCell>
                <TableCell className="text-right font-mono">{fmtPct(row.disk_free_min_percent)}</TableCell>
                <TableCell className="text-center">{statusBadge(status)}</TableCell>
              </TableRow>
            )
          })}
        </TableBody>
      </Table>
    </div>
  )
}

// ─── Alarm Verification ──────────────────────────────────────────────────────

interface AlarmItem {
  alarm_name?: string
  status?: string
  alarm_state?: string
  current_state?: string
  threshold_text?: string
  breach_start_time?: string
  breach_end_time?: string
  ongoing_minutes?: number
  breach_duration_minutes?: number
  should_report?: boolean
  recommended_action?: string
  reason?: string
  message?: string
}

function alarmRowMeta(item: AlarmItem): { priority: number; label: string; color: string } {
  if (item.status === 'not-found') return { priority: 3, label: 'Not Found', color: 'text-muted-foreground' }
  const action = item.recommended_action
  if (action === 'REPORT_NOW') return { priority: 0, label: 'Report Now', color: 'text-red-500' }
  if (action === 'MONITOR') return { priority: 1, label: 'Monitor', color: 'text-amber-500' }
  if (action === 'NO_REPORT_RECOVERED') return { priority: 2, label: 'Recovered', color: 'text-emerald-500' }
  return { priority: 2, label: 'OK', color: 'text-emerald-500' }
}

function AlarmVerificationDetail({ details }: { details: Record<string, unknown> }) {
  const alarms = (details.alarms ?? []) as AlarmItem[]
  const minMinutes = (details.min_alarm_minutes as number) ?? 10

  const sorted = [...alarms].sort((a, b) => alarmRowMeta(a).priority - alarmRowMeta(b).priority)

  if (alarms.length === 0) {
    return <p className="text-[11px] text-muted-foreground italic">No alarm data</p>
  }

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-muted-foreground">
        <span>Rule: report only alarms in ALARM state ≥ {minMinutes} min</span>
        <span className="text-border">·</span>
        <span>Data source: CloudWatch 24h history</span>
        <span className="text-border">·</span>
        <span className="flex items-center gap-1">
          <span className="inline-block w-2 h-2 rounded-sm bg-orange-500/40" />
          <span className="text-orange-400/80">{'>'}  24 jam = alarm sudah lama aktif, titik mulai di luar history window</span>
        </span>
      </div>

      <div className="overflow-x-auto rounded-md border border-border/40">
      <Table>
        <TableHeader>
          <TableRow className="hover:bg-transparent">
            <TableHead>Status</TableHead>
            <TableHead>Alarm Name</TableHead>
            <TableHead>State</TableHead>
            <TableHead>Threshold</TableHead>
            <TableHead>Time Range</TableHead>
            <TableHead>Duration</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {sorted.map((item, i) => {
            const meta = alarmRowMeta(item)
            const state = item.alarm_state ?? item.current_state ?? 'UNKNOWN'
            const isAlarm = state === 'ALARM'
            const startUnknown = !item.breach_start_time || item.breach_start_time === 'unknown'
            // Alarm in ALARM state with unknown start = has been alarming > 24h (outside history window)
            const isChronicAlarm = isAlarm && startUnknown

            const timeRange = isAlarm
              ? startUnknown ? null : `${item.breach_start_time} – now`
              : item.breach_start_time && !startUnknown && item.breach_end_time && item.breach_end_time !== 'unknown'
              ? `${item.breach_start_time} – ${item.breach_end_time}`
              : null
            const duration = isAlarm
              ? item.ongoing_minutes ? `${item.ongoing_minutes}m ongoing` : null
              : item.breach_duration_minutes ? `${item.breach_duration_minutes}m` : null

            return (
              <TableRow
                key={i}
                className={isChronicAlarm ? 'bg-orange-500/5' : undefined}
              >
                <TableCell className={cn('font-medium text-[11px] whitespace-nowrap', meta.color)}>
                  {meta.label}
                </TableCell>
                <TableCell className="font-mono text-foreground text-[11px] max-w-[220px] truncate">
                  {item.alarm_name ?? '-'}
                </TableCell>
                <TableCell>
                  {state !== 'UNKNOWN'
                    ? statusBadge(state === 'OK' ? 'OK' : state === 'ALARM' ? 'ALARM' : 'WARN')
                    : <span className="text-[11px] text-muted-foreground">—</span>}
                </TableCell>
                <TableCell className="font-mono text-[11px] text-muted-foreground whitespace-nowrap">
                  {item.threshold_text ?? '—'}
                </TableCell>
                <TableCell className="text-[11px] whitespace-nowrap">
                  {isChronicAlarm ? (
                    <span className="inline-flex items-center gap-1">
                      <span className="text-orange-400 font-medium">{'> 24 jam'}</span>
                      <span className="text-[10px] text-orange-400/60 italic">(di luar history window)</span>
                    </span>
                  ) : timeRange ? (
                    <span className="text-muted-foreground">{timeRange}</span>
                  ) : (
                    <span className="text-muted-foreground">—</span>
                  )}
                </TableCell>
                <TableCell className="text-[11px] text-muted-foreground whitespace-nowrap">
                  {duration ?? '—'}
                </TableCell>
              </TableRow>
            )
          })}
        </TableBody>
      </Table>
      </div>

    </div>
  )
}

// ─── Cost Anomaly ────────────────────────────────────────────────────────────

function CostAnomalyDetail({ details }: { details: Record<string, unknown> }) {
  const anomalies = (details.anomalies ?? []) as Array<Record<string, unknown>>
  const totalMonitors = (details.total_monitors as number) ?? 0
  const todayCount = (details.today_anomaly_count as number) ?? 0
  const yesterdayCount = (details.yesterday_anomaly_count as number) ?? 0
  const totalImpact = anomalies.reduce((sum, a) => sum + Number((a.Impact as Record<string,unknown>)?.TotalImpact ?? 0), 0)

  return (
    <div className="space-y-3">
      {/* Stats */}
      <div className="flex gap-4 text-[11px]">
        <span className="text-muted-foreground">Monitors: <span className="text-foreground font-medium">{totalMonitors}</span></span>
        <span className="text-muted-foreground">Today: <span className={cn('font-medium', todayCount > 0 ? 'text-red-500' : 'text-foreground')}>{todayCount}</span></span>
        <span className="text-muted-foreground">Yesterday: <span className={cn('font-medium', yesterdayCount > 0 ? 'text-amber-500' : 'text-foreground')}>{yesterdayCount}</span></span>
        {anomalies.length > 0 && (
          <span className="text-muted-foreground">Total Impact: <span className={cn('font-medium font-mono', totalImpact > 100 ? 'text-red-500' : totalImpact > 0 ? 'text-amber-500' : 'text-foreground')}>{fmtDollar(totalImpact)}</span></span>
        )}
      </div>

      {anomalies.length === 0 ? (
        <p className="text-[11px] text-emerald-500 italic">No anomalies detected</p>
      ) : (
        <div className="space-y-2">
          {anomalies.map((a, i) => {
            const impact = (a.Impact as Record<string, unknown>) ?? {}
            const score = (a.AnomalyScore as Record<string, unknown>) ?? {}
            const rootCauses = (a.RootCauses ?? []) as Array<Record<string, unknown>>
            const impactVal = Number(impact.TotalImpact ?? 0)
            const isHigh = impactVal > 100
            const isMed = impactVal > 20

            return (
              <div key={i} className={cn(
                'rounded-md border px-3 py-2 space-y-2',
                isHigh ? 'border-red-500/30 bg-red-500/5'
                : isMed ? 'border-amber-500/30 bg-amber-500/5'
                : 'border-border/50 bg-muted/20',
              )}>
                {/* Anomaly header */}
                <div className="flex items-start justify-between gap-2">
                  <div>
                    <span className="text-[11px] font-medium text-foreground">{(a.MonitorName as string) ?? '—'}</span>
                    <span className="ml-2 text-[10px] text-muted-foreground">
                      {a.AnomalyStartDate as string} → {a.AnomalyEndDate as string}
                    </span>
                  </div>
                  <div className="flex items-center gap-2 shrink-0">
                    <span className={cn('text-[11px] font-mono font-semibold', isHigh ? 'text-red-500' : isMed ? 'text-amber-500' : 'text-foreground')}>
                      {fmtDollar(impactVal)}
                    </span>
                    <span className="text-[10px] text-muted-foreground">score: {String(score.CurrentScore ?? '-')}</span>
                  </div>
                </div>

                {/* Root causes */}
                {rootCauses.length > 0 && (
                  <div className="space-y-0.5">
                    <p className="text-[10px] text-muted-foreground/60 uppercase tracking-wider font-medium">Root Causes</p>
                    {rootCauses.slice(0, 5).map((rc, j) => (
                      <div key={j} className="flex items-center gap-2 text-[11px] text-muted-foreground">
                        <span className="font-medium text-foreground">{(rc.Service as string) ?? '-'}</span>
                        {rc.Region ? <span className="text-muted-foreground/60">{String(rc.Region)}</span> : null}
                        {rc.UsageType ? <span className="font-mono text-[10px] text-muted-foreground/70">{String(rc.UsageType)}</span> : null}
                        {rc.LinkedAccount ? <span className="font-mono text-[10px] text-muted-foreground/50">acct: {String(rc.LinkedAccount)}</span> : null}
                      </div>
                    ))}
                    {rootCauses.length > 5 && (
                      <p className="text-[10px] text-muted-foreground/50">+{rootCauses.length - 5} more</p>
                    )}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

// ─── GuardDuty ───────────────────────────────────────────────────────────────

function GuardDutyDetail({ details }: { details: Record<string, unknown> }) {
  if (details.status === 'disabled') return <p className="text-[11px] text-muted-foreground italic">GuardDuty is disabled on this account</p>

  const findingsDetails = (details.details ?? []) as Array<Record<string, string>>
  const findingsCount = (details.findings as number) ?? 0

  if (findingsCount === 0) return <p className="text-[11px] text-muted-foreground italic">No findings detected</p>

  return (
    <Table>
      <TableHeader>
        <TableRow className="hover:bg-transparent">
          <TableHead>Severity</TableHead>
          <TableHead>Type</TableHead>
          <TableHead>Title</TableHead>
          <TableHead>Updated</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {findingsDetails.map((d, i) => (
          <TableRow key={i}>
            <TableCell>{statusBadge(d.severity ?? 'UNKNOWN')}</TableCell>
            <TableCell className="font-mono text-foreground text-[11px]">{d.type}</TableCell>
            <TableCell className="text-muted-foreground">{d.title}</TableCell>
            <TableCell className="text-muted-foreground">{d.updated}</TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  )
}

// ─── Backup ──────────────────────────────────────────────────────────────────

function BackupDetail({ details }: { details: Record<string, unknown> }) {
  const totalJobs = (details.total_jobs as number) ?? 0
  const completed = (details.completed_jobs as number) ?? 0
  const failed = (details.failed_jobs as number) ?? 0
  const expired = (details.expired_jobs as number) ?? 0
  const jobDetails = (details.job_details ?? []) as Array<Record<string, unknown>>
  const vaults = (details.vaults ?? []) as Array<Record<string, unknown>>

  return (
    <div className="space-y-2">
      <div className="flex gap-3 text-[11px]">
        <span className="text-muted-foreground">Total: {totalJobs}</span>
        <span className="text-emerald-600">Completed: {completed}</span>
        {failed > 0 && <span className="text-red-600">Failed: {failed}</span>}
        {expired > 0 && <span className="text-amber-600">Expired: {expired}</span>}
      </div>

      {/* Vault activity */}
      {vaults.length > 0 && (
        <div className="space-y-2">
          <p className="text-[10px] font-medium text-muted-foreground uppercase tracking-wide">Vaults</p>
          {vaults.map((v, i) => {
            const rp24h = (v.recovery_points_24h as number) ?? 0
            const total = (v.total_recovery_points as number) ?? 0
            const hasError = !!v.error
            const resources = (v.resources_24h ?? []) as string[]
            return (
              <div key={i} className="rounded-md border border-border/40 p-2 space-y-1">
                <div className="flex items-center gap-2 text-[11px]">
                  <span className={cn('font-mono font-bold', hasError ? 'text-red-400' : rp24h > 0 ? 'text-emerald-500' : 'text-amber-400')}>
                    {hasError ? '✗' : rp24h > 0 ? '✓' : '⚠'}
                  </span>
                  <span className="font-mono text-foreground font-medium">{v.vault_name as string}</span>
                  {hasError ? (
                    <span className="text-red-400 text-[10px]">{v.error as string}</span>
                  ) : (
                    <span className="text-muted-foreground">{rp24h} new (24h) / {total} total</span>
                  )}
                </div>
                {resources.length > 0 && (
                  <div className="pl-4 space-y-0.5">
                    {resources.map((r, j) => {
                      // r may be a string (old history) or {arn, name, type} (new)
                      const isObj = typeof r === 'object' && r !== null
                      const arn = isObj ? (r as Record<string,string>).arn : r as string
                      const name = isObj ? (r as Record<string,string>).name : (arn.includes('/') ? arn.split('/').pop() : arn.split(':').pop())
                      const type = isObj ? (r as Record<string,string>).type : ''
                      return (
                        <p key={j} className="text-[10px] font-mono text-muted-foreground/70 truncate" title={arn}>
                          {type && <span className="text-muted-foreground/40 mr-1">[{type}]</span>}
                          {name}
                        </p>
                      )
                    })}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}

      {jobDetails.length > 0 && (
        <Table>
          <TableHeader>
            <TableRow className="hover:bg-transparent">
              <TableHead>State</TableHead>
              <TableHead>Resource</TableHead>
              <TableHead>Time</TableHead>
              <TableHead>Reason</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {jobDetails.map((j, i) => {
              const state = (j.state as string) ?? ''
              return (
                <TableRow key={i}>
                  <TableCell>{statusBadge(state === 'COMPLETED' ? 'OK' : state)}</TableCell>
                  <TableCell className="font-mono text-foreground text-[11px]">{(j.resource_label as string) ?? '-'}</TableCell>
                  <TableCell className="text-muted-foreground">{(j.created_wib as string) ?? '-'}</TableCell>
                  <TableCell className="text-muted-foreground text-[11px] max-w-[200px] truncate">{(j.reason as string) || '-'}</TableCell>
                </TableRow>
              )
            })}
          </TableBody>
        </Table>
      )}
    </div>
  )
}

// ─── CloudWatch Alarms ───────────────────────────────────────────────────────

function CloudWatchDetail({ details }: { details: Record<string, unknown> }) {
  const count = (details.count as number) ?? 0
  const alarmDetails = (details.details ?? []) as Array<Record<string, string>>

  if (count === 0) return <p className="text-[11px] text-muted-foreground italic">All monitoring systems normal</p>

  return (
    <Table>
      <TableHeader>
        <TableRow className="hover:bg-transparent">
          <TableHead>Alarm Name</TableHead>
          <TableHead>Reason</TableHead>
          <TableHead>Updated</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {alarmDetails.map((a, i) => (
          <TableRow key={i}>
            <TableCell className="font-mono text-foreground">{a.name}</TableCell>
            <TableCell className="text-muted-foreground text-[11px] max-w-[300px] truncate">{a.reason}</TableCell>
            <TableCell className="text-muted-foreground">{a.updated}</TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  )
}

// ─── Notifications ───────────────────────────────────────────────────────────

function NotifEventTable({ events, label }: { events: Array<Record<string, unknown>>, label: string }) {
  if (events.length === 0) return null
  return (
    <div className="space-y-1">
      <p className="text-[11px] font-medium text-muted-foreground uppercase tracking-wider">{label}</p>
      <Table>
        <TableHeader>
          <TableRow className="hover:bg-transparent">
            <TableHead className="text-[11px]">Time (WIB)</TableHead>
            <TableHead className="text-[11px]">Type</TableHead>
            <TableHead className="text-[11px]">Headline</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {events.map((e, i) => {
            const notifEvent = (e.notificationEvent ?? {}) as Record<string, unknown>
            const meta = (notifEvent.sourceEventMetadata ?? {}) as Record<string, string>
            const msg = (notifEvent.messageComponents ?? {}) as Record<string, string>
            const creationTime = e.creationTime as string | undefined
            return (
              <TableRow key={i}>
                <TableCell className="text-[11px] text-muted-foreground whitespace-nowrap align-top">
                  {creationTime ? formatDateFull(creationTime) : '-'}
                </TableCell>
                <TableCell className="font-mono text-[11px] text-foreground whitespace-nowrap align-top">{meta.eventType ?? '-'}</TableCell>
                <TableCell className="text-[11px] align-top">
                  <p className="text-foreground">{msg.headline ?? '-'}</p>
                  {msg.paragraphSummary && (
                    <p className="mt-1 text-muted-foreground leading-relaxed">{msg.paragraphSummary}</p>
                  )}
                </TableCell>
              </TableRow>
            )
          })}
        </TableBody>
      </Table>
    </div>
  )
}

function NotificationDetail({ details }: { details: Record<string, unknown> }) {
  const recentCount = (details.recent_count as number) ?? 0
  const regularCount = (details.regular_count as number) ?? 0
  const totalManaged = (details.total_managed as number) ?? 0
  const recentEvents = (details.recent_events ?? []) as Array<Record<string, unknown>>
  const allEvents = (details.all_events ?? []) as Array<Record<string, unknown>>
  const regularEvents = (details.regular_events ?? []) as Array<Record<string, unknown>>

  const managedToShow = recentEvents.length > 0 ? recentEvents : allEvents.slice(0, 5)

  return (
    <div className="space-y-3">
      <div className="flex gap-3 text-[11px] text-muted-foreground">
        <span>Recent 12h: <span className="font-medium text-foreground">{recentCount}</span></span>
        <span>Managed total: <span className="font-medium text-foreground">{totalManaged}</span></span>
        <span>Regular: <span className="font-medium text-foreground">{regularCount}</span></span>
      </div>
      {managedToShow.length === 0 && regularEvents.length === 0 ? (
        <p className="text-[11px] text-muted-foreground italic">No notifications</p>
      ) : (
        <>
          <NotifEventTable
            events={managedToShow}
            label={recentEvents.length > 0 ? 'Recent (12h)' : 'Latest managed'}
          />
          <NotifEventTable events={regularEvents.slice(0, 5)} label="Regular notifications" />
        </>
      )}
    </div>
  )
}

// ─── Main Dispatcher ─────────────────────────────────────────────────────────

export function CheckDetailView({ checkName, details }: CheckDetailViewProps) {
  if (!details) return null

  // Error state — fall back to text
  if (details.status === 'error') {
    return (
      <p className="text-[11px] text-red-600">
        Error: {(details.error as string) ?? 'Unknown error'}
      </p>
    )
  }

  if (checkName === 'daily-arbel' || checkName === 'daily-arbel-rds' || checkName === 'daily-arbel-ec2') {
    return <ArbelDetail details={details} />
  }
  if (checkName === 'aws-utilization-3core' || checkName === 'ec2_utilization') {
    return <UtilizationDetail details={details} />
  }
  if (checkName === 'cost') {
    return <CostAnomalyDetail details={details} />
  }
  if (checkName === 'guardduty') {
    return <GuardDutyDetail details={details} />
  }
  if (checkName === 'backup') {
    return <BackupDetail details={details} />
  }
  if (checkName === 'cloudwatch') {
    return <CloudWatchDetail details={details} />
  }
  if (checkName === 'notifications') {
    return <NotificationDetail details={details} />
  }
  if (checkName === 'alarm_verification') {
    return <AlarmVerificationDetail details={details} />
  }

  return null
}
