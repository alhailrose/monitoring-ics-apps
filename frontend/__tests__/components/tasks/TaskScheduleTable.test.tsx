import { render, screen, fireEvent } from '@testing-library/react'
import { TaskScheduleTable } from '@/components/tasks/TaskScheduleTable'
import type { ReportSchedule } from '@/components/dashboard/ReportReminder'

// Use a past time so "overdue" logic triggers deterministically
const oldTime = new Date(Date.now() - 20 * 3600 * 1000).toISOString()
const recentTime = new Date(Date.now() - 1 * 3600 * 1000).toISOString()

const schedules: ReportSchedule[] = [
  {
    customerId: 'c1',
    customerName: 'Acme Corp',
    scheduleTimes: ['08:00', '19:00'],
    lastReportSentAt: oldTime,
    lastCheckRunAt: recentTime,
    reportSentWithLastRun: false,
  },
  {
    customerId: 'c2',
    customerName: 'Beta Ltd',
    scheduleTimes: ['09:00'],
    lastReportSentAt: recentTime,
    lastCheckRunAt: recentTime,
    reportSentWithLastRun: true,
  },
]

describe('TaskScheduleTable', () => {
  it('renders customer names', () => {
    render(<TaskScheduleTable schedules={schedules} />)
    expect(screen.getByText('Acme Corp')).toBeInTheDocument()
    expect(screen.getByText('Beta Ltd')).toBeInTheDocument()
  })

  it('renders scheduled time chips', () => {
    render(<TaskScheduleTable schedules={schedules} />)
    expect(screen.getAllByText('08:00').length).toBeGreaterThan(0)
    expect(screen.getAllByText('19:00').length).toBeGreaterThan(0)
    expect(screen.getAllByText('09:00').length).toBeGreaterThan(0)
  })

  it('shows Edit button per row', () => {
    render(<TaskScheduleTable schedules={schedules} />)
    expect(screen.getAllByRole('button', { name: /edit/i }).length).toBe(2)
  })

  it('opens inline editor on Edit click', () => {
    render(<TaskScheduleTable schedules={schedules} />)
    fireEvent.click(screen.getAllByRole('button', { name: /edit/i })[0])
    expect(screen.getByLabelText('New schedule time')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /done/i })).toBeInTheDocument()
  })

  it('closes editor after Done click', () => {
    render(<TaskScheduleTable schedules={schedules} />)
    fireEvent.click(screen.getAllByRole('button', { name: /edit/i })[0])
    fireEvent.click(screen.getByRole('button', { name: /done/i }))
    expect(screen.queryByLabelText('New schedule time')).not.toBeInTheDocument()
  })

  it('can remove a time', () => {
    render(<TaskScheduleTable schedules={schedules} />)
    fireEvent.click(screen.getAllByRole('button', { name: /edit/i })[0])
    // Remove 08:00
    fireEvent.click(screen.getByRole('button', { name: 'Remove 08:00' }))
    // 08:00 chip in editor should be gone
    expect(screen.queryByRole('button', { name: 'Remove 08:00' })).not.toBeInTheDocument()
  })

  it('shows empty message when no schedules', () => {
    render(<TaskScheduleTable schedules={[]} />)
    expect(screen.getByText('No customers found.')).toBeInTheDocument()
  })
})
