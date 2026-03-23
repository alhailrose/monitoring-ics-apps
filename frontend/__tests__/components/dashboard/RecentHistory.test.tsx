import { render, screen } from '@testing-library/react'
import { RecentHistory } from '@/components/dashboard/RecentHistory'
import type { CheckRunSummary } from '@/lib/types/api'

const mockRuns: CheckRunSummary[] = [
  {
    check_run_id: 'run-1',
    check_name: 'cloudwatch_alarms',
    check_mode: 'specific',
    created_at: '2024-01-15T10:30:00Z',
    execution_time_seconds: 12.5,
    slack_sent: false,
    results_summary: { total: 3, ok: 2, warn: 1, error: 0 },
  },
  {
    check_run_id: 'run-2',
    check_name: 'guardduty',
    check_mode: 'all',
    created_at: '2024-01-14T08:00:00Z',
    execution_time_seconds: 5.2,
    slack_sent: true,
    results_summary: { total: 2, ok: 1, warn: 0, error: 1 },
  },
]

describe('RecentHistory', () => {
  it('shows empty state when no runs', () => {
    render(<RecentHistory runs={[]} />)
    expect(screen.getByText('No runs yet')).toBeInTheDocument()
  })

  it('renders check names', () => {
    render(<RecentHistory runs={mockRuns} />)
    expect(screen.getByText('cloudwatch_alarms')).toBeInTheDocument()
    expect(screen.getByText('guardduty')).toBeInTheDocument()
  })

  it('renders check mode', () => {
    render(<RecentHistory runs={mockRuns} />)
    expect(screen.getByText(/specific/)).toBeInTheDocument()
    expect(screen.getAllByText(/\ball\b/).length).toBeGreaterThan(0)
  })

  it('renders result status counts', () => {
    render(<RecentHistory runs={mockRuns} />)
    // run-1 has ok:2, warn:1 — run-2 has ok:1, error:1
    const okCounts = screen.getAllByText('2')
    expect(okCounts.length).toBeGreaterThan(0)
  })

  it('renders View all link', () => {
    render(<RecentHistory runs={mockRuns} />)
    expect(screen.getByRole('link', { name: /view all/i })).toBeInTheDocument()
  })
})
