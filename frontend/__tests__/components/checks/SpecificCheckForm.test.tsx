import { render, screen, fireEvent } from '@testing-library/react'
import { SpecificCheckForm } from '@/components/checks/SpecificCheckForm'
import type { Customer } from '@/lib/types/api'

jest.mock('@/app/(dashboard)/checks/actions', () => ({
  runChecks: jest.fn(),
}))

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
        aws_auth_mode: 'sso',
        role_arn: null,
        external_id: null,
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
        aws_auth_mode: 'sso',
        role_arn: null,
        external_id: null,
        config_extra: {},
      },
    ],
  },
]

describe('SpecificCheckForm', () => {
  it('renders check cards for all 9 check types', () => {
    render(<SpecificCheckForm customers={mockCustomers} />)
    expect(screen.getByRole('button', { name: /guardduty/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /rds utilization/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /ec2 utilization/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /alarm verification/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /daily budget/i })).toBeInTheDocument()
  })

  it('renders collapsible customer headers', () => {
    render(<SpecificCheckForm customers={mockCustomers} />)
    expect(screen.getByText('Acme Corp')).toBeInTheDocument()
    expect(screen.getByText('Beta Inc')).toBeInTheDocument()
  })

  it('renders search input for accounts', () => {
    render(<SpecificCheckForm customers={mockCustomers} />)
    expect(screen.getByPlaceholderText(/search accounts/i)).toBeInTheDocument()
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
    expect(screen.getByText(/no customers available/i)).toBeInTheDocument()
  })
})
