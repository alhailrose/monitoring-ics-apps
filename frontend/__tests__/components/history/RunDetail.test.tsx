import React from 'react'
import { render, screen } from '@testing-library/react'
import { RunDetail } from '@/components/history/RunDetail'
import type { CheckRunDetail } from '@/lib/types/api'

const mockRun: CheckRunDetail = {
  check_run_id: 'run-1',
  check_mode: 'all',
  check_name: 'daily-arbel',
  created_at: '2026-03-22T10:00:00Z',
  execution_time_seconds: 12.5,
  slack_sent: false,
  customer: { id: 'cust-1', name: 'test-customer', display_name: 'Test Customer' },
  results_summary: { total: 2, ok: 1, warn: 0, error: 1 },
  results: [
    {
      customer_id: 'cust-1',
      account: { id: 'acc-1', profile_name: 'prod', display_name: 'Production' },
      check_name: 'daily-arbel',
      status: 'OK',
      summary: 'All good',
      output: '',
      error_class: null,
    },
    {
      customer_id: 'cust-1',
      account: { id: 'acc-2', profile_name: 'staging', display_name: 'Staging' },
      check_name: 'daily-arbel',
      status: 'ERROR',
      summary: 'Session expired',
      output: '',
      error_class: 'sso_expired',
    },
  ],
}

describe('RunDetail', () => {
  it('renders run metadata', () => {
    render(<RunDetail run={mockRun} />)
    expect(screen.getByText('12.50s')).toBeInTheDocument()
  })

  it('renders customer card with matrix table', () => {
    render(<RunDetail run={mockRun} />)
    expect(screen.getByText('Test Customer')).toBeInTheDocument()
    expect(screen.getByText('daily-arbel')).toBeInTheDocument()
  })

  it('renders account headers in matrix', () => {
    render(<RunDetail run={mockRun} />)
    expect(screen.getByText('Production')).toBeInTheDocument()
    expect(screen.getByText('Staging')).toBeInTheDocument()
  })

  it('renders empty state when no results', () => {
    render(<RunDetail run={{ ...mockRun, results: [] }} />)
    expect(screen.getByText('No results recorded')).toBeInTheDocument()
  })
})
