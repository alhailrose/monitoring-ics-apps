import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import type { Customer } from '@/lib/types/api'
import { SessionStatusPopup } from '@/components/checks/SessionStatusPopup'

const fetchMock = jest.fn()

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
        profile_name: 'acme-prod',
        account_id: '123456789012',
        display_name: 'Acme Prod',
        is_active: true,
        auth_method: 'profile',
        role_arn: null,
        external_id: null,
        aws_access_key_id: null,
        region: 'ap-southeast-1',
        config_extra: {},
      },
      {
        id: 'acc-2',
        profile_name: 'acme-dr',
        account_id: '210987654321',
        display_name: 'Acme DR',
        is_active: true,
        auth_method: 'profile',
        role_arn: null,
        external_id: null,
        aws_access_key_id: null,
        region: 'ap-southeast-1',
        config_extra: {},
      },
    ],
  },
  {
    id: 'cust-2',
    name: 'beta',
    display_name: 'Beta Inc',
    checks: ['guardduty'],
    slack_enabled: false,
    slack_channel: null,
    report_mode: 'summary',
    label: null,
    accounts: [
      {
        id: 'acc-3',
        profile_name: 'beta-main',
        account_id: '999999999999',
        display_name: 'Beta Main',
        is_active: true,
        auth_method: 'profile',
        role_arn: null,
        external_id: null,
        aws_access_key_id: null,
        region: 'ap-southeast-1',
        config_extra: {},
      },
    ],
  },
  {
    id: 'cust-3',
    name: 'ffi',
    display_name: 'Frisian Flag Indonesia',
    checks: ['guardduty'],
    slack_enabled: false,
    slack_channel: null,
    report_mode: 'summary',
    label: null,
    accounts: [
      {
        id: 'acc-4',
        profile_name: 'ffi-access',
        account_id: '555555555555',
        display_name: 'FFI Access Key',
        is_active: true,
        auth_method: 'access_key',
        role_arn: null,
        external_id: null,
        aws_access_key_id: 'AKIA_TEST',
        region: 'ap-southeast-1',
        config_extra: {},
      },
    ],
  },
]

describe('SessionStatusPopup', () => {
  beforeEach(() => {
    global.fetch = fetchMock as unknown as typeof fetch
    fetchMock.mockReset()
    fetchMock.mockResolvedValue({
      ok: true,
      json: async () => ({
        profiles: [
          { profile_name: 'acme-prod', status: 'ok' },
          { profile_name: 'acme-dr', status: 'expired' },
          { profile_name: 'beta-main', status: 'ok' },
        ],
      }),
    })
  })

  it('opens popup and shows customer-level statuses', async () => {
    render(<SessionStatusPopup customers={mockCustomers} />)

    expect(screen.queryByText('Acme Corp')).not.toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: /session status/i }))

    expect(await screen.findByText('Acme Corp')).toBeInTheDocument()
    expect(screen.getByText('Beta Inc')).toBeInTheDocument()
    expect(screen.getByText('Frisian Flag Indonesia')).toBeInTheDocument()
    expect(screen.getByText('Expired')).toBeInTheDocument()
    expect(screen.getByText('Active')).toBeInTheDocument()
    expect(screen.getByText('N/A (Non-SSO)')).toBeInTheDocument()
    expect(screen.getByText('1/2 active')).toBeInTheDocument()
    expect(screen.getByText('1 non-SSO account')).toBeInTheDocument()
    expect(screen.getByText(/Last checked:/i)).toBeInTheDocument()
  })

  it('shows error and retries loading', async () => {
    fetchMock
      .mockResolvedValueOnce({ ok: false, status: 500 })
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          profiles: [{ profile_name: 'acme-prod', status: 'ok' }],
        }),
      })

    render(<SessionStatusPopup customers={mockCustomers} />)
    fireEvent.click(screen.getByRole('button', { name: /session status/i }))

    expect(await screen.findByText(/Failed to load session status/i)).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: /retry/i }))

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledTimes(2)
    })
    expect(await screen.findByText('Acme Corp')).toBeInTheDocument()
  })
})
