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
import { cn } from '@/lib/utils'

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

function fmtBytes(val: unknown, unit: 'GB' | 'MB' = 'GB'): string {
  if (typeof val !== 'number') return '-'
  if (unit === 'GB') return `${(val / (1024 ** 3)).toFixed(2)} GB`
  return `${(val / (1024 ** 2)).toFixed(2)} MB`
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

  return (
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
  if (name === 'DatabaseConnections') {
    const val = last ?? avg
    return val != null ? String(Math.round(val)) : '-'
  }
  if (name === 'BufferCacheHitRatio') {
    const val = avg ?? last
    return val != null ? fmtPct(val) : '-'
  }
  // CPU, ACU, etc.
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
  )
}

// ─── Cost Anomaly ────────────────────────────────────────────────────────────

function CostAnomalyDetail({ details }: { details: Record<string, unknown> }) {
  const anomalies = (details.anomalies ?? []) as Array<Record<string, unknown>>
  const totalMonitors = (details.total_monitors as number) ?? 0
  const todayCount = (details.today_anomaly_count as number) ?? 0
  const yesterdayCount = (details.yesterday_anomaly_count as number) ?? 0

  return (
    <div className="space-y-2">
      <div className="flex gap-3 text-[11px] text-muted-foreground">
        <span>Monitors: {totalMonitors}</span>
        <span>Today: {todayCount}</span>
        <span>Yesterday: {yesterdayCount}</span>
      </div>
      {anomalies.length === 0 ? (
        <p className="text-[11px] text-muted-foreground italic">No anomalies detected</p>
      ) : (
        <Table>
          <TableHeader>
            <TableRow className="hover:bg-transparent">
              <TableHead>Monitor</TableHead>
              <TableHead>Date Range</TableHead>
              <TableHead className="text-right">Impact</TableHead>
              <TableHead className="text-right">Score</TableHead>
              <TableHead>Services</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {anomalies.map((a, i) => {
              const impact = (a.Impact as Record<string, unknown>) ?? {}
              const score = (a.AnomalyScore as Record<string, unknown>) ?? {}
              const rootCauses = (a.RootCauses ?? []) as Array<Record<string, unknown>>
              const services = [...new Set(rootCauses.map((rc) => rc.Service as string).filter(Boolean))]
              return (
                <TableRow key={i}>
                  <TableCell className="font-mono text-foreground">{(a.MonitorName as string) ?? '-'}</TableCell>
                  <TableCell className="text-muted-foreground">{a.AnomalyStartDate as string} ~ {a.AnomalyEndDate as string}</TableCell>
                  <TableCell className={cn('text-right font-mono', Number(impact.TotalImpact ?? 0) > 50 ? 'text-red-600' : '')}>{fmtDollar(impact.TotalImpact)}</TableCell>
                  <TableCell className="text-right font-mono">{String(score.CurrentScore ?? '-')}</TableCell>
                  <TableCell className="text-muted-foreground text-[11px]">{services.slice(0, 3).join(', ') || '-'}</TableCell>
                </TableRow>
              )
            })}
          </TableBody>
        </Table>
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

  return (
    <div className="space-y-2">
      <div className="flex gap-3 text-[11px]">
        <span className="text-muted-foreground">Total: {totalJobs}</span>
        <span className="text-emerald-600">Completed: {completed}</span>
        {failed > 0 && <span className="text-red-600">Failed: {failed}</span>}
        {expired > 0 && <span className="text-amber-600">Expired: {expired}</span>}
      </div>
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

function NotificationDetail({ details }: { details: Record<string, unknown> }) {
  const recentCount = (details.recent_count as number) ?? 0
  const totalManaged = (details.total_managed as number) ?? 0
  const recentEvents = (details.recent_events ?? []) as Array<Record<string, unknown>>
  const allEvents = (details.all_events ?? []) as Array<Record<string, unknown>>

  const events = recentEvents.length > 0 ? recentEvents : allEvents.slice(0, 3)

  return (
    <div className="space-y-2">
      <div className="flex gap-3 text-[11px] text-muted-foreground">
        <span>Recent (12h): {recentCount}</span>
        <span>Total: {totalManaged}</span>
      </div>
      {events.length === 0 ? (
        <p className="text-[11px] text-muted-foreground italic">No notifications</p>
      ) : (
        <Table>
          <TableHeader>
            <TableRow className="hover:bg-transparent">
              <TableHead>Time</TableHead>
              <TableHead>Type</TableHead>
              <TableHead>Headline</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {events.map((e, i) => {
              const notifEvent = (e.notificationEvent ?? {}) as Record<string, unknown>
              const meta = (notifEvent.sourceEventMetadata ?? {}) as Record<string, string>
              const msg = (notifEvent.messageComponents ?? {}) as Record<string, string>
              return (
                <TableRow key={i}>
                  <TableCell className="text-muted-foreground">{(e.creationTime as string) ?? '-'}</TableCell>
                  <TableCell className="font-mono text-foreground text-[11px]">{meta.eventType ?? '-'}</TableCell>
                  <TableCell className="text-muted-foreground text-[11px] max-w-[300px] truncate">{msg.headline ?? '-'}</TableCell>
                </TableRow>
              )
            })}
          </TableBody>
        </Table>
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

  // Fallback: show raw output text
  return null
}
