/**
 * @jest-environment jsdom
 */
import React from 'react'
import { render, screen } from '@testing-library/react'
import { StatCards } from '@/components/dashboard/StatCards'
import type { DashboardSummary } from '@/lib/types/api'

jest.mock('next/link', () => ({ __esModule: true, default: ({ children, href }: { children: React.ReactNode; href: string }) => <a href={href}>{children}</a> }))

const mockSummary: DashboardSummary = {
  customer_id: 'c1',
  window_hours: 24,
  generated_at: '2024-01-01T00:00:00Z',
  since: '2023-12-31T00:00:00Z',
  runs: { total: 42, single: 10, all: 20, arbel: 12, latest_created_at: '2024-01-01T00:00:00Z' },
  results: { total: 100, ok: 80, warn: 15, error: 5, alarm: 0, no_data: 0 },
  findings: { total: 7, by_severity: { CRITICAL: 2, HIGH: 3, MEDIUM: 2 } },
  metrics: { total: 50, by_status: { ok: 40, warn: 8, error: 2 } },
  top_checks: [{ check_name: 'ec2_list', runs: 10 }],
}

describe('StatCards', () => {
  it('renders total runs value from summary', () => {
    render(<StatCards summary={mockSummary} reportSchedules={[]} />)
    expect(screen.getByText('42')).toBeInTheDocument()
  })

  it('renders skeleton placeholders when summary is null', () => {
    const { container } = render(<StatCards summary={null} reportSchedules={[]} />)
    // Skeletons render as divs with animate-pulse class
    const skeletons = container.querySelectorAll('[data-slot="skeleton"]')
    expect(skeletons.length).toBeGreaterThan(0)
  })

  it('renders findings total', () => {
    render(<StatCards summary={mockSummary} reportSchedules={[]} />)
    expect(screen.getByText('7')).toBeInTheDocument()
  })

  it('renders metrics total', () => {
    render(<StatCards summary={mockSummary} reportSchedules={[]} />)
    expect(screen.getByText('50')).toBeInTheDocument()
  })

  it('shows overdue banner when schedules are overdue', () => {
    const overdueSchedule = {
      customerId: 'c1',
      customerName: 'Acme',
      scheduleTimes: ['08:00'],
      lastReportSentAt: new Date(Date.now() - 30 * 3600 * 1000).toISOString(),
      lastCheckRunAt: null,
      reportSentWithLastRun: false,
    }
    render(<StatCards summary={mockSummary} reportSchedules={[overdueSchedule]} />)
    expect(screen.getByText(/overdue/i)).toBeInTheDocument()
  })

  it('does not show overdue banner when no schedules are overdue', () => {
    render(<StatCards summary={mockSummary} reportSchedules={[]} />)
    expect(screen.queryByText(/overdue/i)).not.toBeInTheDocument()
  })
})
