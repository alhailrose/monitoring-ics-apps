import { render, screen, fireEvent } from '@testing-library/react'
import { DedicatedCheckForm } from '@/components/checks/DedicatedCheckForm'
import type { Account, Customer } from '@/lib/types/api'

jest.mock('@/app/(dashboard)/checks/actions', () => ({
  runChecks: jest.fn(),
}))

const mockAccount: Account = {
  id: 'acc-1',
  profile_name: 'aryanoble-prod',
  account_id: '123456789012',
  display_name: 'AryaNoble Production',
  is_active: true,
  auth_method: 'profile',
  role_arn: null,
  external_id: null,
        aws_access_key_id: null,
        region: null,
  config_extra: {},
}

const mockCustomer: Customer = {
  id: 'cust-1',
  name: 'aryanoble',
  display_name: 'Arya Noble',
  checks: ['daily-arbel'],
  slack_enabled: false,
  slack_channel: null,
  report_mode: 'summary',
  label: null,
  accounts: [mockAccount],
}

const arbelChecks = [
  { value: 'daily-arbel-rds', label: 'RDS Utilization' },
  { value: 'daily-arbel-ec2', label: 'EC2 Utilization' },
  { value: 'daily-budget', label: 'Daily Budget' },
]

describe('DedicatedCheckForm — account mode (accounts prop)', () => {
  it('renders account toggle buttons when accounts prop provided', () => {
    render(
      <DedicatedCheckForm
        mode="arbel"
        label="Arbel Check"
        accounts={[mockAccount]}
        customers={[mockCustomer]}
        checkNames={arbelChecks}
      />,
    )
    expect(screen.getByText('AryaNoble Production')).toBeInTheDocument()
  })

  it('renders check card buttons when multiple check names provided', () => {
    render(
      <DedicatedCheckForm
        mode="arbel"
        label="Arbel Check"
        accounts={[mockAccount]}
        customers={[mockCustomer]}
        checkNames={arbelChecks}
      />,
    )
    expect(screen.getByRole('button', { name: /rds utilization/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /ec2 utilization/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /daily budget/i })).toBeInTheDocument()
  })

  it('shows time window selector for utilization checks', () => {
    render(
      <DedicatedCheckForm
        mode="arbel"
        label="Arbel Check"
        accounts={[mockAccount]}
        customers={[mockCustomer]}
        checkNames={arbelChecks}
      />,
    )
    // RDS Utilization is first (default selected)
    expect(screen.getByRole('button', { name: '1h' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '3h' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '12h' })).toBeInTheDocument()
  })

  it('hides time window when non-utilization check selected', () => {
    render(
      <DedicatedCheckForm
        mode="arbel"
        label="Arbel Check"
        accounts={[mockAccount]}
        customers={[mockCustomer]}
        checkNames={arbelChecks}
      />,
    )
    // Click Daily Budget (non-utilization)
    fireEvent.click(screen.getByRole('button', { name: /daily budget/i }))
    expect(screen.queryByRole('button', { name: '1h' })).not.toBeInTheDocument()
  })

  it('does not render check select when only one check name', () => {
    render(
      <DedicatedCheckForm
        mode="huawei"
        label="Huawei Check"
        accounts={[mockAccount]}
        customers={[mockCustomer]}
        checkNames={[{ value: 'huawei-ecs-util', label: 'ECS Utilization' }]}
      />,
    )
    expect(screen.queryByLabelText('Check')).not.toBeInTheDocument()
  })

  it('renders run button with label', () => {
    render(
      <DedicatedCheckForm
        mode="arbel"
        label="Arbel Check"
        accounts={[mockAccount]}
        customers={[mockCustomer]}
        checkNames={arbelChecks}
      />,
    )
    expect(screen.getByRole('button', { name: /run arbel check/i })).toBeInTheDocument()
  })

  it('run button is enabled when account pre-selected', () => {
    render(
      <DedicatedCheckForm
        mode="arbel"
        label="Arbel Check"
        accounts={[mockAccount]}
        customers={[mockCustomer]}
        checkNames={arbelChecks}
      />,
    )
    expect(screen.getByRole('button', { name: /run arbel check/i })).not.toBeDisabled()
  })

  it('shows empty message when no accounts', () => {
    render(
      <DedicatedCheckForm
        mode="arbel"
        label="Arbel Check"
        accounts={[]}
        customers={[mockCustomer]}
        checkNames={arbelChecks}
      />,
    )
    expect(screen.getByText(/no accounts available/i)).toBeInTheDocument()
  })
})

describe('DedicatedCheckForm — customer mode (customers prop)', () => {
  it('renders customer toggle buttons when customers prop used', () => {
    render(
      <DedicatedCheckForm
        mode="arbel"
        label="Arbel Check"
        customers={[mockCustomer]}
        checkNames={arbelChecks}
      />,
    )
    expect(screen.getByText('Arya Noble')).toBeInTheDocument()
  })

  it('renders description when provided', () => {
    render(
      <DedicatedCheckForm
        mode="arbel"
        label="Arbel Check"
        description="Runs Arbel-specific checks"
        customers={[mockCustomer]}
        checkNames={arbelChecks}
      />,
    )
    expect(screen.getByText('Runs Arbel-specific checks')).toBeInTheDocument()
  })
})
