import { render, screen } from '@testing-library/react'
import { CustomerDetailView } from '@/components/customers/CustomerDetailView'
import type { Customer, CheckRunSummary, Finding } from '@/lib/types/api'

jest.mock('next/navigation', () => ({
  useRouter: () => ({
    refresh: jest.fn(),
  }),
}))

const mockSessionsHealth = {
  healthMap: {},
  healthLoading: false,
  healthError: false,
  lastCheckedAt: null,
  refresh: jest.fn(),
}

jest.mock('@/app/(dashboard)/customers/actions', () => ({
  deleteAccount: jest.fn(),
}))

jest.mock('@/components/customers/useSessionsHealth', () => ({
  useSessionsHealth: () => mockSessionsHealth,
}))

const customer: Customer = {
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
      aws_access_key_id: null,
      role_arn: null,
      external_id: null,
      region: 'ap-southeast-1',
      config_extra: {},
    },
  ],
}

const findings: Finding[] = []
const runs: CheckRunSummary[] = []

describe('CustomerDetailView', () => {
  beforeEach(() => {
    mockSessionsHealth.healthMap = {}
    mockSessionsHealth.healthLoading = false
    mockSessionsHealth.healthError = false
  })

  it('shows account mutation actions for super_user', () => {
    render(
      <CustomerDetailView
        customer={customer}
        findings={findings}
        findingsTotal={0}
        runs={runs}
        runsTotal={0}
        role="super_user"
      />,
    )

    expect(screen.getByRole('button', { name: /add account/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /edit/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /delete/i })).toBeInTheDocument()
  })

  it('hides account mutation actions for user role', () => {
    render(
      <CustomerDetailView
        customer={customer}
        findings={findings}
        findingsTotal={0}
        runs={runs}
        runsTotal={0}
        role="user"
      />,
    )

    expect(screen.queryByRole('button', { name: /add account/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /edit/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /delete/i })).not.toBeInTheDocument()
  })

  it('shows expired session indicator for expired profile health', () => {
    mockSessionsHealth.healthMap = {
      prod: {
        profile_name: 'prod',
        account_id: '123456789012',
        display_name: 'Production',
        status: 'expired',
        error: '',
        sso_session: 'acme-sso',
        login_command: 'aws sso login --sso-session acme-sso',
      },
    }

    render(
      <CustomerDetailView
        customer={customer}
        findings={findings}
        findingsTotal={0}
        runs={runs}
        runsTotal={0}
        role="super_user"
      />,
    )

    expect(screen.getByText(/1 expired session/i)).toBeInTheDocument()
    expect(screen.getByText('expired')).toBeInTheDocument()
  })
})
