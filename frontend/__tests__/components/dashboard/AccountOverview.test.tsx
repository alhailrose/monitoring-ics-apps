import { render, screen, fireEvent } from '@testing-library/react'
import { AccountOverview } from '@/components/dashboard/AccountOverview'
import type { Finding, CheckResult } from '@/lib/types/api'

jest.mock('next/navigation', () => ({
  useRouter: () => ({ replace: jest.fn() }),
  useSearchParams: () => ({ toString: () => '' }),
  usePathname: () => '/dashboard',
}))

const mockFindings: Finding[] = [
  {
    id: 'f1',
    check_run_id: 'run-1',
    account: { id: 'acc-1', profile_name: 'prod', display_name: 'Production Account' },
    check_name: 'guardduty',
    finding_key: 'gd-001',
    severity: 'CRITICAL',
    title: 'Unusual API activity',
    description: 'GuardDuty detected unusual calls.',
    created_at: '2024-01-15T10:00:00Z',
  },
]

const mockResults: CheckResult[] = [
  {
    customer_id: 'cust-1',
    account: { id: 'acc-1', profile_name: 'prod', display_name: 'Production Account' },
    check_name: 'cloudwatch_alarms',
    status: 'ERROR',
    summary: 'Alarms in ALARM state',
    output: '',
  },
  {
    customer_id: 'cust-1',
    account: { id: 'acc-2', profile_name: 'staging', display_name: 'Staging Account' },
    check_name: 'guardduty',
    status: 'OK',
    summary: 'No findings',
    output: '',
  },
]

describe('AccountOverview', () => {
  it('shows all clean message when no findings and all OK results', () => {
    const okResults: CheckResult[] = [
      { customer_id: 'c', account: { id: 'a1', profile_name: 'p', display_name: 'Acc A' }, check_name: 'gd', status: 'OK', summary: '', output: '' },
    ]
    render(<AccountOverview findings={[]} results={okResults} />)
    expect(screen.getByText('All accounts are clean')).toBeInTheDocument()
  })

  it('renders accounts with issues', () => {
    render(<AccountOverview findings={mockFindings} results={mockResults} />)
    expect(screen.getByText('Production Account')).toBeInTheDocument()
  })

  it('does not show clean accounts in the list', () => {
    render(<AccountOverview findings={mockFindings} results={mockResults} />)
    // Staging is OK — should not appear since it has no findings and status is OK
    expect(screen.queryByText('Staging Account')).not.toBeInTheDocument()
  })

  it('shows Detail button per account', () => {
    render(<AccountOverview findings={mockFindings} results={mockResults} />)
    expect(screen.getByRole('button', { name: /detail/i })).toBeInTheDocument()
  })

  it('expands detail panel on Detail click', () => {
    render(<AccountOverview findings={mockFindings} results={mockResults} />)
    fireEvent.click(screen.getByRole('button', { name: /detail/i }))
    expect(screen.getByText('Unusual API activity')).toBeInTheDocument()
    expect(screen.getByText('Alarms in ALARM state')).toBeInTheDocument()
  })

  it('shows run name when provided', () => {
    render(<AccountOverview findings={[]} results={[]} runName="guardduty" />)
    expect(screen.getByText(/guardduty/)).toBeInTheDocument()
  })
})
