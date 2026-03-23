import Link from 'next/link'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { StatusBadge } from '@/components/common/StatusBadge'
import { SeverityBadge } from '@/components/common/SeverityBadge'
import { HugeiconsIcon } from '@hugeicons/react'
import { Alert01Icon, ArrowRight01Icon } from '@hugeicons/core-free-icons'
import { cn } from '@/lib/utils'
import { isOverdue } from '@/lib/schedule-utils'
import type { DashboardSummary, CheckStatus, FindingSeverity, MetricStatus } from '@/lib/types/api'
import type { ReportSchedule } from '@/lib/schedule-utils'

interface StatCardsProps {
  summary: DashboardSummary | null
  reportSchedules: ReportSchedule[]
  currentCustomerId?: string
}

const RESULT_STATUSES: CheckStatus[] = ['OK', 'WARN', 'ERROR']
const SEVERITIES: FindingSeverity[] = ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']
const METRIC_STATUSES: MetricStatus[] = ['ok', 'warn', 'error']

const METRIC_COLORS: Record<MetricStatus, string> = {
  ok:    'text-green-400',
  warn:  'text-yellow-400',
  error: 'text-red-400',
}

export function StatCards({ summary, reportSchedules, currentCustomerId }: StatCardsProps) {
  if (!summary) {
    return (
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <Card key={i}>
            <CardHeader className="pb-2"><Skeleton className="h-4 w-24" /></CardHeader>
            <CardContent><Skeleton className="h-8 w-16 mb-2" /><Skeleton className="h-4 w-full" /></CardContent>
          </Card>
        ))}
      </div>
    )
  }

  const overdueCount = reportSchedules.filter(isOverdue).length

  return (
    <div className="space-y-3">
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {/* Card 1: Total Runs */}
        <Card>
          <CardHeader className="pb-1">
            <CardTitle className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Total Runs</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold">{summary.runs.total}</p>
            <p className="text-xs text-muted-foreground mt-1">
              Latest:{' '}
              {summary.runs.latest_created_at
                ? new Date(summary.runs.latest_created_at).toLocaleDateString('en-GB', { day: '2-digit', month: 'short' })
                : '—'}
            </p>
          </CardContent>
        </Card>

        {/* Card 2: Results */}
        <Card>
          <CardHeader className="pb-1">
            <CardTitle className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Results</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold">{summary.results.total}</p>
            <div className="flex flex-wrap gap-1.5 mt-2">
              {RESULT_STATUSES.map((s) => {
                const count = summary.results[s.toLowerCase() as keyof typeof summary.results] as number
                return count > 0 ? (
                  <span key={s} className="flex items-center gap-1">
                    <StatusBadge status={s} />
                    <span className="text-xs text-muted-foreground">{count}</span>
                  </span>
                ) : null
              })}
            </div>
          </CardContent>
        </Card>

        {/* Card 3: Findings */}
        <Card>
          <CardHeader className="pb-1">
            <CardTitle className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Findings</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold">{summary.findings.total}</p>
            <div className="flex flex-wrap gap-1.5 mt-2">
              {SEVERITIES.map((s) => {
                const count = summary.findings.by_severity[s]
                return count ? (
                  <span key={s} className="flex items-center gap-1">
                    <SeverityBadge severity={s} />
                    <span className="text-xs text-muted-foreground">{count}</span>
                  </span>
                ) : null
              })}
            </div>
          </CardContent>
        </Card>

        {/* Card 4: Metrics */}
        <Card>
          <CardHeader className="pb-1">
            <CardTitle className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Metrics</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold">{summary.metrics.total}</p>
            <div className="flex flex-wrap gap-2 mt-2">
              {METRIC_STATUSES.map((s) => {
                const count = summary.metrics.by_status[s]
                return count ? (
                  <span key={s} className={cn('text-xs font-medium', METRIC_COLORS[s])}>
                    {s.toUpperCase()} {count}
                  </span>
                ) : null
              })}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Schedule overdue banner — only shown when there are overdue schedules */}
      {overdueCount > 0 && (
        <div className="flex items-center justify-between rounded-lg border border-yellow-500/30 bg-yellow-500/5 px-4 py-2.5">
          <div className="flex items-center gap-2">
            <HugeiconsIcon icon={Alert01Icon} strokeWidth={2} className="size-4 text-yellow-400 shrink-0" />
            <span className="text-sm text-yellow-400 font-medium">
              {overdueCount} report schedule{overdueCount !== 1 ? 's are' : ' is'} overdue
            </span>
          </div>
          <Link
            href="/tasks"
            className="flex items-center gap-1 text-xs text-yellow-400/80 hover:text-yellow-400 transition-colors"
          >
            Manage schedules
            <HugeiconsIcon icon={ArrowRight01Icon} strokeWidth={2} className="size-3" />
          </Link>
        </div>
      )}
    </div>
  )
}
