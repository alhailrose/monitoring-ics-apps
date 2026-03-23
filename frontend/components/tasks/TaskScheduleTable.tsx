'use client'
// Client component — inline schedule editor per customer (mock until backend ready)

import * as React from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { HugeiconsIcon } from '@hugeicons/react'
import {
  CheckmarkCircle01Icon,
  Alert01Icon,
  Clock01Icon,
  Add01Icon,
  Delete01Icon,
  Settings01Icon,
} from '@hugeicons/core-free-icons'
import { cn } from '@/lib/utils'
import { isOverdue } from '@/lib/schedule-utils'
import type { ReportSchedule } from '@/lib/schedule-utils'

interface TaskScheduleTableProps {
  schedules: ReportSchedule[]
}

function formatRelative(iso: string | null): string {
  if (!iso) return 'Never'
  const diff = Date.now() - new Date(iso).getTime()
  const hours = Math.floor(diff / 3600000)
  const mins = Math.floor((diff % 3600000) / 60000)
  if (hours > 0) return `${hours}h ago`
  return `${mins}m ago`
}

function isValidTime(t: string): boolean {
  return /^([01]\d|2[0-3]):[0-5]\d$/.test(t)
}

function ScheduleRow({ schedule }: { schedule: ReportSchedule }) {
  const [times, setTimes] = React.useState<string[]>(schedule.scheduleTimes ?? [])
  const [editing, setEditing] = React.useState(false)
  const [newTime, setNewTime] = React.useState('')
  const [error, setError] = React.useState('')

  const overdue = isOverdue({ ...schedule, scheduleTimes: times })

  const addTime = () => {
    const t = newTime.trim()
    if (!isValidTime(t)) { setError('Format: HH:mm (e.g. 08:00)'); return }
    if (times.includes(t)) { setError('Already added'); return }
    const sorted = [...times, t].sort()
    setTimes(sorted)
    setNewTime('')
    setError('')
  }

  const removeTime = (t: string) => setTimes((prev) => prev.filter((x) => x !== t))

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') addTime()
  }

  return (
    <div className="rounded-lg border border-border overflow-hidden">
      {/* Row header */}
      <div className="flex items-center justify-between gap-4 px-4 py-3">
        <div className="flex items-center gap-3 min-w-0">
          {overdue
            ? <HugeiconsIcon icon={Alert01Icon} strokeWidth={2} className="size-4 shrink-0 text-yellow-400" />
            : schedule.reportSentWithLastRun
            ? <HugeiconsIcon icon={CheckmarkCircle01Icon} strokeWidth={2} className="size-4 shrink-0 text-green-400" />
            : <HugeiconsIcon icon={Clock01Icon} strokeWidth={2} className="size-4 shrink-0 text-muted-foreground" />
          }
          <div className="min-w-0">
            <p className="text-sm font-medium text-foreground truncate">{schedule.customerName}</p>
            <p className="text-xs text-muted-foreground mt-0.5">
              Last sent: {formatRelative(schedule.lastReportSentAt)}
            </p>
          </div>
        </div>

        <div className="flex shrink-0 items-center gap-2">
          {/* Time chips */}
          <div className="flex flex-wrap gap-1">
            {times.length === 0 ? (
              <span className="text-xs text-muted-foreground">No schedule</span>
            ) : (
              times.map((t) => (
                <span
                  key={t}
                  className="rounded-full bg-muted px-2 py-0.5 text-xs font-mono text-foreground"
                >
                  {t}
                </span>
              ))
            )}
          </div>

          <Badge className={cn(
            'text-xs shrink-0',
            overdue
              ? 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30'
              : 'bg-green-500/20 text-green-400 border-green-500/30'
          )}>
            {overdue ? 'Overdue' : 'On schedule'}
          </Badge>

          <Button
            variant="outline"
            size="sm"
            className="h-7 px-2 text-xs gap-1"
            onClick={() => setEditing((v) => !v)}
          >
            <HugeiconsIcon icon={Settings01Icon} strokeWidth={2} className="size-3" />
            Edit
          </Button>
        </div>
      </div>

      {/* Inline editor */}
      {editing && (
        <div className="border-t border-border bg-muted/30 px-4 py-3 space-y-3">
          <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
            Scheduled times
          </p>

          {/* Existing times */}
          <div className="flex flex-wrap gap-2">
            {times.length === 0 && (
              <span className="text-xs text-muted-foreground">No times set — add one below</span>
            )}
            {times.map((t) => (
              <div
                key={t}
                className="flex items-center gap-1 rounded-full border border-border bg-background px-2.5 py-1"
              >
                <span className="font-mono text-xs text-foreground">{t}</span>
                <button
                  type="button"
                  onClick={() => removeTime(t)}
                  aria-label={`Remove ${t}`}
                  className="text-muted-foreground hover:text-destructive transition-colors"
                >
                  <HugeiconsIcon icon={Delete01Icon} strokeWidth={2} className="size-3" />
                </button>
              </div>
            ))}
          </div>

          {/* Add new time */}
          <div className="flex items-center gap-2">
            <Input
              type="time"
              value={newTime}
              onChange={(e) => { setNewTime(e.target.value); setError('') }}
              onKeyDown={handleKeyDown}
              className="h-7 w-32 text-xs font-mono"
              aria-label="New schedule time"
            />
            <Button
              size="sm"
              variant="outline"
              className="h-7 px-2 text-xs gap-1"
              onClick={addTime}
            >
              <HugeiconsIcon icon={Add01Icon} strokeWidth={2} className="size-3" />
              Add
            </Button>
            <Button
              size="sm"
              className="h-7 px-3 text-xs"
              onClick={() => { setEditing(false); setError('') }}
            >
              Done
            </Button>
          </div>
          {error && <p className="text-xs text-destructive">{error}</p>}
        </div>
      )}
    </div>
  )
}

export function TaskScheduleTable({ schedules }: TaskScheduleTableProps) {
  const overdueCount = schedules.filter(isOverdue).length

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-medium">Report Schedules</CardTitle>
          {overdueCount > 0 && (
            <span className="flex items-center gap-1 text-xs font-medium text-yellow-400">
              <HugeiconsIcon icon={Alert01Icon} strokeWidth={2} className="size-3" />
              {overdueCount} overdue
            </span>
          )}
        </div>
        <p className="text-xs text-muted-foreground mt-1">
          Set specific times for daily report delivery per customer.
        </p>
      </CardHeader>
      <CardContent>
        {schedules.length === 0 ? (
          <p className="text-sm text-muted-foreground">No customers found.</p>
        ) : (
          <div className="space-y-2">
            {schedules.map((s) => (
              <ScheduleRow key={s.customerId} schedule={s} />
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
