import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { SpecificCheckForm } from '@/components/checks/SpecificCheckForm'
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
    accounts: [
      {
        id: 'acc-1',
        profile_name: 'prod',
        account_id: '123456789012',
        display_name: 'Production',
        is_active: true,
        auth_method: 'profile',
        role_arn: null,
        external_id: null,
        aws_access_key_id: null,
        region: null,
        config_extra: {},
        alarm_names: ['HighCPU', 'LowMemory'],
      },
    ],
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
    accounts: [
      {
        id: 'acc-2',
        profile_name: 'staging',
        account_id: '987654321098',
        display_name: 'Staging',
        is_active: true,
        auth_method: 'profile',
        role_arn: null,
        external_id: null,
        aws_access_key_id: null,
        region: null,
        config_extra: {},
      },
    ],
  },
]

describe('SpecificCheckForm', () => {
  beforeEach(() => {
    mockRunChecks.mockReset()
    mockRunChecks.mockResolvedValue({
      data: {
        mode: 'single',
        check_runs: [],
        execution_time_seconds: 0.5,
        results: [],
        consolidated_outputs: {},
        customer_labels: {},
        backup_overviews: {},
      },
    })
  })

  it('renders check cards for legacy and new AWS checks', () => {
    render(<SpecificCheckForm customers={mockCustomers} />)
    expect(screen.getByRole('button', { name: /guardduty/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /rds utilization/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /ec2 utilization/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /alarm verification/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /daily budget/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /lambda/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /ecs services/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /s3 buckets/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /vpc security/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /iam hygiene/i })).toBeInTheDocument()
  })

  it('renders collapsible customer headers', () => {
    render(<SpecificCheckForm customers={mockCustomers} />)
    expect(screen.getByText('Acme Corp')).toBeInTheDocument()
    expect(screen.getByText('Beta Inc')).toBeInTheDocument()
  })

  it('renders search input for accounts', () => {
    render(<SpecificCheckForm customers={mockCustomers} />)
    expect(screen.getByPlaceholderText(/cari akun atau customer/i)).toBeInTheDocument()
  })

  it('shows time window selector for utilization checks', () => {
    render(<SpecificCheckForm customers={mockCustomers} />)
    // Select RDS Utilization
    fireEvent.click(screen.getByRole('button', { name: /rds utilization/i }))
    expect(screen.getByRole('button', { name: '1h' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '3h' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '12h' })).toBeInTheDocument()
  })

  it('does not show time window for non-utilization checks', () => {
    render(<SpecificCheckForm customers={mockCustomers} />)
    // GuardDuty is selected by default
    expect(screen.queryByRole('button', { name: '1h' })).not.toBeInTheDocument()
  })

  it('renders run button enabled when customers exist', () => {
    render(<SpecificCheckForm customers={mockCustomers} />)
    expect(screen.getByRole('button', { name: /run check/i })).not.toBeDisabled()
  })

  it('run button is disabled when no customers', () => {
    render(<SpecificCheckForm customers={[]} />)
    expect(screen.getByRole('button', { name: /run check/i })).toBeDisabled()
  })

  it('renders with empty customers list', () => {
    render(<SpecificCheckForm customers={[]} />)
    expect(screen.getAllByText(/no customers available/i).length).toBeGreaterThan(0)
  })

  it('submits through the synchronous checks action', async () => {
    render(<SpecificCheckForm customers={mockCustomers} />)

    fireEvent.click(screen.getByText('Production'))
    fireEvent.click(screen.getByRole('button', { name: /run check/i }))

    await waitFor(() => {
      expect(mockRunChecks).toHaveBeenCalledTimes(1)
    })
  })

  it('shows history CTA after successful run when check_run_id exists', async () => {
    mockRunChecks.mockResolvedValueOnce({
      data: {
        mode: 'single',
        check_run_id: 'run-123',
        check_runs: [{ customer_id: 'cust-1', check_run_id: 'run-123', slack_sent: false }],
        execution_time_seconds: 0.5,
        results: [],
        consolidated_outputs: {},
        customer_labels: {},
        backup_overviews: {},
      },
    })

    render(<SpecificCheckForm customers={mockCustomers} />)
    fireEvent.click(screen.getByText('Production'))
    fireEvent.click(screen.getByRole('button', { name: /run check/i }))

    const link = await screen.findByRole('link', { name: /view latest run/i })
    expect(link).toHaveAttribute('href', '/history?run=run-123')
  })

})
