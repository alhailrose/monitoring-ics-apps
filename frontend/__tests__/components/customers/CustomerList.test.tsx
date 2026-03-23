import { render, screen } from '@testing-library/react'
import { CustomerList } from '@/components/customers/CustomerList'
import type { Customer } from '@/lib/types/api'

jest.mock('@/app/(dashboard)/customers/actions', () => ({
  createCustomer: jest.fn(),
  updateCustomer: jest.fn(),
  deleteCustomer: jest.fn(),
  addAccount: jest.fn(),
  updateAccount: jest.fn(),
  deleteAccount: jest.fn(),
}))

// Mock fetch for sessions-health (lazy loaded in useEffect)
global.fetch = jest.fn(() => Promise.resolve({ ok: false } as Response))

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
    slack_enabled: true,
    slack_channel: '#alerts',
    report_mode: 'summary',
    label: null,
    accounts: [],
  },
]

describe('CustomerList', () => {
  it('renders customer names', () => {
    render(<CustomerList customers={mockCustomers} role="user" />)
    expect(screen.getByText('Acme Corp')).toBeInTheDocument()
    expect(screen.getByText('Beta Inc')).toBeInTheDocument()
  })

  it('renders EmptyState when customers array is empty', () => {
    render(<CustomerList customers={[]} role="user" />)
    expect(screen.getByText('No customers found')).toBeInTheDocument()
  })

  it('does NOT show New Customer button for user role', () => {
    render(<CustomerList customers={mockCustomers} role="user" />)
    expect(screen.queryByRole('button', { name: /new customer/i })).not.toBeInTheDocument()
  })

  it('shows New Customer button for super_user role', () => {
    render(<CustomerList customers={mockCustomers} role="super_user" />)
    expect(screen.getByRole('button', { name: /new customer/i })).toBeInTheDocument()
  })

  it('shows Slack badge for slack-enabled customers', () => {
    render(<CustomerList customers={mockCustomers} role="user" />)
    expect(screen.getByText('Slack')).toBeInTheDocument()
  })

  it('renders without errors when customers have accounts', () => {
    const customersWithAccounts: Customer[] = [
      {
        ...mockCustomers[0],
        accounts: [
          {
            id: 'acc-1',
            profile_name: 'prod',
            account_id: '123456789012',
            display_name: 'Production',
            is_active: true,
            aws_auth_mode: 'aws_login',
            role_arn: null,
            external_id: null,
            config_extra: {},
          },
        ],
      },
    ]
    render(<CustomerList customers={customersWithAccounts} role="user" />)
    expect(screen.getByText('Acme Corp')).toBeInTheDocument()
  })
})
