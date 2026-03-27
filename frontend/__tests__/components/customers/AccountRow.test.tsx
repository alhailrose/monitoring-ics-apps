import { render, screen } from '@testing-library/react'
import { AccountRow } from '@/components/customers/AccountRow'
import type { Account, ProfileHealth } from '@/lib/types/api'

const mockAccount: Account = {
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
}

const mockHealth: ProfileHealth = {
  profile_name: 'prod',
  account_id: '123456789012',
  display_name: 'Production',
  status: 'ok',
  error: '',
  sso_session: null,
  login_command: '',
}

const noop = () => {}

describe('AccountRow', () => {
  it('renders account display name and account ID', () => {
    render(
      <AccountRow
        account={mockAccount}
        healthMap={{ prod: mockHealth }}
        role="user"
        onEdit={noop}
        onDelete={noop}
      />,
    )
    expect(screen.getByText('Production')).toBeInTheDocument()
    expect(screen.getByText('123456789012')).toBeInTheDocument()
  })

  it('renders AuthModeBadge with correct mode', () => {
    render(
      <AccountRow
        account={mockAccount}
        healthMap={{ prod: mockHealth }}
        role="user"
        onEdit={noop}
        onDelete={noop}
      />,
    )
    expect(screen.getByText('sso')).toBeInTheDocument()
  })

  it('does not show actions menu for user role', () => {
    render(
      <AccountRow
        account={mockAccount}
        healthMap={{}}
        role="user"
        onEdit={noop}
        onDelete={noop}
      />,
    )
    // No dropdown trigger button for non-super_user
    expect(screen.queryByRole('button')).not.toBeInTheDocument()
  })

  it('shows actions dropdown trigger for super_user role', () => {
    render(
      <AccountRow
        account={mockAccount}
        healthMap={{}}
        role="super_user"
        onEdit={noop}
        onDelete={noop}
      />,
    )
    expect(screen.getByRole('button')).toBeInTheDocument()
  })

  it('applies opacity class when account is inactive', () => {
    const inactive = { ...mockAccount, is_active: false }
    const { container } = render(
      <AccountRow
        account={inactive}
        healthMap={{}}
        role="user"
        onEdit={noop}
        onDelete={noop}
      />,
    )
    expect(container.firstChild).toHaveClass('opacity-45')
  })

  it('shows inactive label when account is not active', () => {
    const inactive = { ...mockAccount, is_active: false }
    render(
      <AccountRow
        account={inactive}
        healthMap={{}}
        role="user"
        onEdit={noop}
        onDelete={noop}
      />,
    )
    expect(screen.getByText('inactive')).toBeInTheDocument()
  })

  it('shows session status when health data is available', () => {
    render(
      <AccountRow
        account={mockAccount}
        healthMap={{ prod: mockHealth }}
        role="user"
        onEdit={noop}
        onDelete={noop}
      />,
    )
    // SessionStatusBadge renders for 'ok' status
    expect(screen.getByText(/ok/i)).toBeInTheDocument()
  })

  it('shows skeleton when healthLoading is true', () => {
    const { container } = render(
      <AccountRow
        account={mockAccount}
        healthMap={{}}
        healthLoading={true}
        role="user"
        onEdit={noop}
        onDelete={noop}
      />,
    )
    // Skeleton renders an element with animate-pulse
    expect(container.querySelector('.animate-pulse')).toBeInTheDocument()
  })
})
