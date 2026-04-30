import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { CustomerList } from '@/components/customers/CustomerList'
import type { Customer } from '@/lib/types/api'

jest.mock('next/navigation', () => ({
  useRouter: () => ({ push: jest.fn() }),
}))

jest.mock('@/app/(dashboard)/customers/actions', () => ({
  createCustomer: jest.fn(),
  updateCustomer: jest.fn(),
  deleteCustomer: jest.fn(),
  addAccount: jest.fn(),
  updateAccount: jest.fn(),
  deleteAccount: jest.fn(),
}))

const fetchMock = jest.fn() as jest.MockedFunction<typeof fetch>
global.fetch = fetchMock

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
  beforeEach(() => {
    fetchMock.mockReset()
    window.sessionStorage.clear()
  })

  it('renders customer names', () => {
    render(<CustomerList customers={mockCustomers} role="user" />)
    expect(screen.getByText('Acme Corp')).toBeInTheDocument()
    expect(screen.getByText('Beta Inc')).toBeInTheDocument()
  })

  it('does not auto-fetch session health on mount', () => {
    fetchMock.mockResolvedValue({
      ok: true,
      json: async () => ({ total_profiles: 0, ok: 0, expired: 0, error: 0, profiles: [], sso_sessions: {} }),
    } as Response)

    render(<CustomerList customers={mockCustomers} role="user" />)

    expect(fetchMock).not.toHaveBeenCalled()
    expect(screen.getByRole('button', { name: /refresh session/i })).toBeInTheDocument()
  })

  it('refreshes session health only when refresh button is clicked', async () => {
    fetchMock.mockResolvedValue({
      ok: true,
      json: async () => ({
        total_profiles: 2,
        ok: 0,
        expired: 2,
        error: 0,
        profiles: [
          {
            profile_name: 'prod',
            account_id: '123456789012',
            display_name: 'Production',
            status: 'expired',
            error: '',
            sso_session: 'sadewa-sso',
            login_command: 'aws sso login --sso-session sadewa-sso',
          },
          {
            profile_name: 'staging',
            account_id: '210987654321',
            display_name: 'Staging',
            status: 'expired',
            error: '',
            sso_session: 'sadewa-sso',
            login_command: 'aws sso login --sso-session sadewa-sso',
          },
        ],
        sso_sessions: {},
      }),
    } as Response)

    render(<CustomerList customers={mockCustomers} role="user" />)
    expect(fetchMock).not.toHaveBeenCalled()

    await userEvent.click(screen.getByRole('button', { name: /refresh session/i }))

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledTimes(1)
      expect(fetchMock).toHaveBeenCalledWith('/api/sessions-health')
    })

    await waitFor(() => {
      const matches = screen.queryAllByText((_, node) =>
        (node?.textContent ?? '').includes('2 sessions expired'),
      )
      expect(matches.length).toBeGreaterThan(0)
    })
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

  it('does not render legacy Slack badge', () => {
    render(<CustomerList customers={mockCustomers} role="user" />)
    expect(screen.queryByText('Slack')).not.toBeInTheDocument()
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
    render(<CustomerList customers={customersWithAccounts} role="user" />)
    expect(screen.getByText('Acme Corp')).toBeInTheDocument()
  })
})
