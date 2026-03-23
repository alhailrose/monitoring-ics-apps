import React from 'react'
import { render, screen } from '@testing-library/react'
import { RunTable } from '@/components/history/RunTable'
import type { CheckRunSummary } from '@/lib/types/api'

jest.mock('next/navigation', () => ({
  useRouter: () => ({ push: jest.fn() }),
  useSearchParams: () => new URLSearchParams(),
  usePathname: () => '/history',
}))

jest.mock('next/link', () => ({
  __esModule: true,
  default: ({ href, children }: { href: string; children: React.ReactNode }) => (
    <a href={href}>{children}</a>
  ),
}))

const mockRun = (overrides: Partial<CheckRunSummary> = {}): CheckRunSummary => ({
  check_run_id: 'run-1',
  check_mode: 'all',
  check_name: 'daily-arbel',
  created_at: '2026-03-22T10:00:00Z',
  execution_time_seconds: 12.5,
  slack_sent: false,
  results_summary: { total: 3, ok: 2, warn: 1, error: 0 },
  ...overrides,
})

describe('RunTable', () => {
  it('renders run rows', () => {
    render(
      <RunTable
        runs={[mockRun(), mockRun({ check_run_id: 'run-2', check_name: 'guardduty' })]}
        total={2}
        page={1}
        pageSize={20}
      />,
    )
    expect(screen.getByText('daily-arbel')).toBeInTheDocument()
    expect(screen.getByText('guardduty')).toBeInTheDocument()
  })

  it('shows EmptyState when runs array is empty', () => {
    render(<RunTable runs={[]} total={0} page={1} pageSize={20} />)
    expect(screen.getByText('No runs found')).toBeInTheDocument()
    expect(screen.getByText('Run a check to see history here')).toBeInTheDocument()
  })

  it('renders check mode', () => {
    render(<RunTable runs={[mockRun({ check_mode: 'single' })]} total={1} page={1} pageSize={20} />)
    expect(screen.getByText('single')).toBeInTheDocument()
  })

  it('renders duration', () => {
    render(<RunTable runs={[mockRun({ execution_time_seconds: 7.3 })]} total={1} page={1} pageSize={20} />)
    expect(screen.getByText('7.30s')).toBeInTheDocument()
  })

  it('links to run detail page', () => {
    render(<RunTable runs={[mockRun()]} total={1} page={1} pageSize={20} />)
    expect(screen.getByRole('link', { name: 'daily-arbel' })).toHaveAttribute('href', '/history/run-1')
  })
})
