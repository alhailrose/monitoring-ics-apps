import React from 'react'
import { render, screen } from '@testing-library/react'
import { MetricsTable } from '@/components/metrics/MetricsTable'
import type { MetricSample } from '@/lib/types/api'

jest.mock('next/navigation', () => ({
  useRouter: () => ({ push: jest.fn() }),
  useSearchParams: () => new URLSearchParams(),
  usePathname: () => '/metrics',
}))

const mockMetric = (overrides: Partial<MetricSample> = {}): MetricSample => ({
  id: '1',
  check_run_id: 'run-1',
  account: { id: 'acc-1', profile_name: 'prod', display_name: 'Production' },
  check_name: 'daily-arbel',
  metric_name: 'cpu_utilization',
  metric_status: 'ok',
  value_num: 42.5,
  unit: '%',
  resource_role: 'primary',
  resource_id: 'i-1234',
  resource_name: 'web-server',
  service_type: 'ec2',
  section_name: 'compute',
  created_at: '2026-03-22T10:00:00Z',
  ...overrides,
})

describe('MetricsTable', () => {
  it('renders metric rows', () => {
    render(
      <MetricsTable
        metrics={[mockMetric(), mockMetric({ id: '2', metric_name: 'memory_usage' })]}
        total={2}
        page={1}
        pageSize={20}
      />,
    )
    expect(screen.getByText('cpu_utilization')).toBeInTheDocument()
    expect(screen.getByText('memory_usage')).toBeInTheDocument()
    expect(screen.getAllByText('Production').length).toBeGreaterThan(0)
  })

  it('shows EmptyState when metrics array is empty', () => {
    render(
      <MetricsTable metrics={[]} total={0} page={1} pageSize={20} />,
    )
    expect(screen.getByText('No metrics')).toBeInTheDocument()
    expect(screen.getByText('Run a check to collect metrics')).toBeInTheDocument()
  })

  it('renders status badge', () => {
    render(
      <MetricsTable
        metrics={[mockMetric({ metric_status: 'warn' })]}
        total={1}
        page={1}
        pageSize={20}
      />,
    )
    expect(screen.getByText('WARN')).toBeInTheDocument()
  })

  it('renders value with unit', () => {
    render(
      <MetricsTable
        metrics={[mockMetric({ value_num: 99, unit: 'MB' })]}
        total={1}
        page={1}
        pageSize={20}
      />,
    )
    expect(screen.getByText(/99.*MB/)).toBeInTheDocument()
  })
})
