'use client'
// Client component — schedule reminder card on dashboard
// TODO: Replace with real API call to GET /api/v1/tasks/schedules?customer_id=...

import Link from 'next/link'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { HugeiconsIcon } from '@hugeicons/react'
import { CheckmarkCircle01Icon, Alert01Icon, Clock01Icon, ArrowRight01Icon } from '@hugeicons/core-free-icons'
import { cn } from '@/lib/utils'
import { isOverdue } from '@/lib/schedule-utils'
import type { ReportSchedule } from '@/lib/schedule-utils'

export type { ReportSchedule }

interface ReportReminderProps {
  schedules: ReportSchedule[]
  currentCustomerId?: string
}

function formatRelative(iso: string | null): string {
  if (!iso) return 'Never'
  const diff = Date.now() - new Date(iso).getTime()
  const hours = Math.floor(diff / 3600000)
  const mins = Math.floor((diff % 3600000) / 60000)
  if (hours > 0) return `${hours}h ago`
  return `${mins}m ago`
}

export function ReportReminder({ schedules = [], currentCustomerId }: ReportReminderProps) {
  const overdueCount = schedules.filter(isOverdue).length

  return (
    <Card className={cn(overdueCount > 0 && 'border-yellow-500/40')}>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-medium text-muted-foreground">Report Schedule</CardTitle>
          <div className="flex items-center gap-2">
            {overdueCount > 0 && (
              <span className="flex items-center gap-1 text-xs font-medium text-yellow-400">
                <HugeiconsIcon icon={Alert01Icon} strokeWidth={2} className="size-3" />
                {overdueCount} overdue
              </span>
            )}
            <Link
              href="/tasks"
              className="flex items-center gap-0.5 text-xs text-muted-foreground hover:text-foreground transition-colors"
            >
              Manage
              <HugeiconsIcon icon={ArrowRight01Icon} strokeWidth={2} className="size-3" />
            </Link>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-2">
        {schedules.length === 0 ? (
          <p className="text-xs text-muted-foreground">No schedules configured</p>
        ) : (
          schedules.map((s) => {
            const overdue = isOverdue(s)
            const isCurrent = s.customerId === currentCustomerId
            return (
              <div
                key={s.customerId}
                className={cn(
                  'flex items-center justify-between rounded-md px-2 py-1.5 text-xs',
                  isCurrent && 'bg-muted/50',
                  overdue ? 'text-yellow-400' : 'text-muted-foreground',
                )}
              >
                <div className="flex items-center gap-1.5 min-w-0">
                  {overdue
                    ? <HugeiconsIcon icon={Alert01Icon} strokeWidth={2} className="size-3 shrink-0 text-yellow-400" />
                    : s.reportSentWithLastRun
                    ? <HugeiconsIcon icon={CheckmarkCircle01Icon} strokeWidth={2} className="size-3 shrink-0 text-green-400" />
                    : <HugeiconsIcon icon={Clock01Icon} strokeWidth={2} className="size-3 shrink-0" />
                  }
                  <span className="truncate font-medium">{s.customerName}</span>
                </div>
                <div className="flex shrink-0 items-center gap-2 ml-2">
                  <span className="text-[10px] opacity-70">
                    {s.scheduleTimes.length > 0 ? s.scheduleTimes.join(', ') : 'No schedule'}
                  </span>
                  <span className={cn('text-[10px]', overdue ? 'text-yellow-400' : 'text-green-400')}>
                    {formatRelative(s.lastReportSentAt)}
                  </span>
                </div>
              </div>
            )
          })
        )}
        <p className="text-[10px] text-muted-foreground/50 pt-1 border-t border-border">
          Schedule config coming soon
        </p>
      </CardContent>
    </Card>
  )
}
