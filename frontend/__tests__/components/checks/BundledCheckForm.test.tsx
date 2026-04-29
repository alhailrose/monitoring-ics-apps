import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { BundledCheckForm } from '@/components/checks/BundledCheckForm'
import { runChecks } from '@/app/(dashboard)/checks/actions'
import type { Customer } from '@/lib/types/api'

jest.mock('@/app/(dashboard)/checks/actions', () => ({
  runChecks: jest.fn(),
}))

const mockRunChecks = jest.mocked(runChecks)

const mockCustomers: Customer[] = [
  {
    id: 'cust-1',
    name: 'acme',
    display_name: 'Acme Corp',
    checks: ['guardduty'],
    slack_enabled: false,
    slack_channel: null,
    report_mode: 'summary',
    label: null,
    accounts: [],
  },
  {
    id: 'cust-2',
    name: 'beta',
    display_name: 'Beta Inc',
    checks: [],
    slack_enabled: false,
    slack_channel: null,
    report_mode: 'summary',
    label: null,
    accounts: [],
  },
]

describe('BundledCheckForm', () => {
  beforeEach(() => {
    mockRunChecks.mockReset()
    mockRunChecks.mockResolvedValue({
      data: {
        mode: 'all',
        check_runs: [],
        execution_time_seconds: 0.5,
        results: [],
        consolidated_outputs: {},
        customer_labels: {},
        backup_overviews: {},
      },
    })
  })

  it('renders mode select', () => {
    render(<BundledCheckForm customers={mockCustomers} />)
    expect(screen.getByLabelText('Mode')).toBeInTheDocument()
  })

  it('shows all and arbel options in mode select', () => {
    render(<BundledCheckForm customers={mockCustomers} />)
    expect(screen.getAllByText('All Checks').length).toBeGreaterThan(0)
    expect(screen.getByText('Arbel Suite')).toBeInTheDocument()
  })

  it('renders customer toggle buttons', () => {
    render(<BundledCheckForm customers={mockCustomers} />)
    expect(screen.getByRole('button', { name: /acme corp/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /beta inc/i })).toBeInTheDocument()
  })

  it('run button is disabled when no customer selected', () => {
    render(<BundledCheckForm customers={mockCustomers} />)
    expect(screen.getByRole('button', { name: /run checks/i })).toBeDisabled()
  })

  it('renders with empty customers list', () => {
    render(<BundledCheckForm customers={[]} />)
    expect(screen.getByRole('button', { name: /run checks/i })).toBeInTheDocument()
  })

  it('submits through the synchronous checks action', async () => {
    render(<BundledCheckForm customers={mockCustomers} />)

    fireEvent.click(screen.getByRole('button', { name: /acme corp/i }))
    fireEvent.click(screen.getByRole('button', { name: /run checks/i }))

    await waitFor(() => {
      expect(mockRunChecks).toHaveBeenCalledTimes(1)
    })
  })

  it('shows history CTA after successful run when check_run_id exists', async () => {
    mockRunChecks.mockResolvedValueOnce({
      data: {
        mode: 'all',
        check_run_id: 'run-999',
        check_runs: [{ customer_id: 'cust-1', check_run_id: 'run-999', slack_sent: false }],
        execution_time_seconds: 1.2,
        results: [],
        consolidated_outputs: {},
        customer_labels: {},
        backup_overviews: {},
      },
    })

    render(<BundledCheckForm customers={mockCustomers} />)
    fireEvent.click(screen.getByRole('button', { name: /acme corp/i }))
    fireEvent.click(screen.getByRole('button', { name: /run checks/i }))

    const link = await screen.findByRole('link', { name: /view latest run/i })
    expect(link).toHaveAttribute('href', '/history?run=run-999')
  })
})
