import { render, screen } from '@testing-library/react'
import { ReportReminder } from '@/components/dashboard/ReportReminder'
import type { ReportSchedule } from '@/components/dashboard/ReportReminder'

const now = new Date().toISOString()
// Use a time far in the past so isOverdue triggers regardless of current clock
const oldTime = new Date(Date.now() - 30 * 3600 * 1000).toISOString()

const schedules: ReportSchedule[] = [
  {
    customerId: 'c1',
    customerName: 'Acme Corp',
    scheduleTimes: ['08:00', '19:00'],
    lastReportSentAt: oldTime, // overdue — last sent 30h ago
    lastCheckRunAt: now,
    reportSentWithLastRun: false,
  },
  {
    customerId: 'c2',
    customerName: 'Beta Ltd',
    scheduleTimes: ['09:00'],
    lastReportSentAt: now, // not overdue — just sent
    lastCheckRunAt: now,
    reportSentWithLastRun: true,
  },
]

describe('ReportReminder', () => {
  it('renders customer names', () => {
    render(<ReportReminder schedules={schedules} />)
    expect(screen.getByText('Acme Corp')).toBeInTheDocument()
    expect(screen.getByText('Beta Ltd')).toBeInTheDocument()
  })

  it('shows overdue count when schedules are overdue', () => {
    render(<ReportReminder schedules={schedules} />)
    expect(screen.getByText('1 overdue')).toBeInTheDocument()
  })

  it('shows scheduled times for each schedule', () => {
    render(<ReportReminder schedules={schedules} />)
    expect(screen.getByText('08:00, 19:00')).toBeInTheDocument()
    expect(screen.getByText('09:00')).toBeInTheDocument()
  })

  it('shows no schedules message when empty', () => {
    render(<ReportReminder schedules={[]} />)
    expect(screen.getByText('No schedules configured')).toBeInTheDocument()
  })
})
