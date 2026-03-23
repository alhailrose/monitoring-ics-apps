import { render, screen, fireEvent } from '@testing-library/react'
import { ResultsTable } from '@/components/checks/ResultsTable'
import type { ExecuteResponse } from '@/lib/types/api'

const mockData: ExecuteResponse = {
  check_runs: [{ customer_id: 'cust-1', check_run_id: 'run-1', slack_sent: false }],
  execution_time_seconds: 3.14,
  results: [
    {
      customer_id: 'cust-1',
      account: { id: 'acc-1', profile_name: 'prod', display_name: 'Production Account' },
      check_name: 'guardduty',
      status: 'OK',
      summary: 'No findings',
      output: 'Detailed guardduty output here',
    },
    {
      customer_id: 'cust-1',
      account: { id: 'acc-2', profile_name: 'staging', display_name: 'Staging Account' },
      check_name: 'guardduty',
      status: 'ERROR',
      summary: 'SSO session expired',
      output: '',
      error_class: 'sso_expired',
    },
  ],
  consolidated_outputs: {},
  backup_overviews: {},
}

describe('ResultsTable', () => {
  it('renders execution time and result count', () => {
    render(<ResultsTable data={mockData} />)
    expect(screen.getByText(/3\.14s/)).toBeInTheDocument()
    expect(screen.getByText(/2 results/)).toBeInTheDocument()
  })

  it('renders account display names', () => {
    render(<ResultsTable data={mockData} />)
    expect(screen.getByText('Production Account')).toBeInTheDocument()
    expect(screen.getByText('Staging Account')).toBeInTheDocument()
  })

  it('renders status badges', () => {
    render(<ResultsTable data={mockData} />)
    expect(screen.getByText('OK')).toBeInTheDocument()
    expect(screen.getByText('ERROR')).toBeInTheDocument()
  })

  it('renders AuthErrorBadge when error_class is present', () => {
    render(<ResultsTable data={mockData} />)
    expect(screen.getByText('Login required')).toBeInTheDocument()
  })

  it('expands detail on row click', () => {
    render(<ResultsTable data={mockData} />)
    fireEvent.click(screen.getByText('Production Account').closest('tr')!)
    expect(screen.getByText('Detailed guardduty output here')).toBeInTheDocument()
  })

  it('collapses detail on second click', () => {
    render(<ResultsTable data={mockData} />)
    const row = screen.getByText('Production Account').closest('tr')!
    fireEvent.click(row)
    expect(screen.getByText('Detailed guardduty output here')).toBeInTheDocument()
    fireEvent.click(row)
    expect(screen.queryByText('Detailed guardduty output here')).not.toBeInTheDocument()
  })

  it('renders consolidated outputs section when present', () => {
    const dataWithConsolidated: ExecuteResponse = {
      ...mockData,
      consolidated_outputs: { 'cust-1': 'Consolidated report text here' },
    }
    render(<ResultsTable data={dataWithConsolidated} />)
    expect(screen.getByText('Consolidated Reports')).toBeInTheDocument()
  })

  it('does not render consolidated section when empty', () => {
    render(<ResultsTable data={mockData} />)
    expect(screen.queryByText('Consolidated Reports')).not.toBeInTheDocument()
  })
})
