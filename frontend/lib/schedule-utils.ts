// Shared schedule utilities — no 'use client', safe to import in Server Components

export interface ReportSchedule {
  customerId: string
  customerName: string
  /** Scheduled times in HH:mm format, e.g. ["08:00", "19:00"] */
  scheduleTimes: string[]
  lastReportSentAt: string | null
  lastCheckRunAt: string | null
  reportSentWithLastRun: boolean
}

/**
 * Returns true if the most recent scheduled time today (or yesterday) has passed
 * and no report has been sent since then.
 */
export function isOverdue(schedule: ReportSchedule): boolean {
  if (!schedule.scheduleTimes || schedule.scheduleTimes.length === 0) return false

  const now = new Date()

  // Build list of scheduled Date objects for today and yesterday
  const candidates: Date[] = []
  for (const offset of [0, -1]) {
    const d = new Date(now)
    d.setDate(d.getDate() + offset)
    const dateStr = d.toISOString().slice(0, 10)
    for (const t of schedule.scheduleTimes) {
      const [h, m] = t.split(':').map(Number)
      const scheduled = new Date(`${dateStr}T${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:00`)
      if (scheduled <= now) candidates.push(scheduled)
    }
  }

  if (candidates.length === 0) return false

  // Most recent scheduled time that has already passed
  const lastScheduled = candidates.reduce((a, b) => (a > b ? a : b))

  if (!schedule.lastReportSentAt) return true
  return new Date(schedule.lastReportSentAt) < lastScheduled
}
