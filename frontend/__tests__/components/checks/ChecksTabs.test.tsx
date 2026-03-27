import { render, screen } from '@testing-library/react'
import { ChecksTabs } from '@/components/checks/ChecksTabs'
import type { Customer } from '@/lib/types/api'

jest.mock('@/app/(dashboard)/checks/actions', () => ({
  runChecks: jest.fn(),
}))

const mockCustomers: Customer[] = [
  {
    id: 'cust-1',
    name: 'acme',
    display_name: 'Acme Corp',
    checks: ['daily-arbel'],
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
      },
    ],
  },
]

describe('ChecksTabs', () => {
  it('renders all 4 tab triggers', () => {
    render(<ChecksTabs customers={mockCustomers} />)
    expect(screen.getByRole('tab', { name: /specific/i })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: /bundled/i })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: /arbel/i })).toBeInTheDocument()
    expect(screen.getByRole('tab', { name: /huawei/i })).toBeInTheDocument()
  })

  it('shows Specific tab content by default', () => {
    render(<ChecksTabs customers={mockCustomers} />)
    expect(screen.getByRole('tab', { name: /specific/i })).toHaveAttribute('data-state', 'active')
  })
})
