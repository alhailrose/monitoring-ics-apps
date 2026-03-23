import { render, screen, fireEvent } from '@testing-library/react'
import { AccountFindings } from '@/components/dashboard/AccountFindings'
import type { Finding } from '@/lib/types/api'

const mockFindings: Finding[] = [
  {
    id: 'f1',
    check_run_id: 'run-1',
    account: { id: 'acc-1', profile_name: 'prod', display_name: 'Production Account' },
    check_name: 'guardduty',
    finding_key: 'gd-001',
    severity: 'CRITICAL',
    title: 'Unusual API activity detected',
    description: 'GuardDuty detected unusual API calls from an IAM user.',
    created_at: '2024-01-15T10:00:00Z',
  },
  {
    id: 'f2',
    check_run_id: 'run-1',
    account: { id: 'acc-1', profile_name: 'prod', display_name: 'Production Account' },
    check_name: 'cloudwatch_alarms',
    finding_key: 'cw-001',
    severity: 'HIGH',
    title: 'CPU alarm triggered',
    description: 'EC2 instance CPU exceeded threshold.',
    created_at: '2024-01-15T10:00:00Z',
  },
  {
    id: 'f3',
    check_run_id: 'run-1',
    account: { id: 'acc-2', profile_name: 'staging', display_name: 'Staging Account' },
    check_name: 'notifications',
    finding_key: 'notif-001',
    severity: 'MEDIUM',
    title: 'Unread notification',
    description: 'There are unread AWS notifications.',
    created_at: '2024-01-15T10:00:00Z',
  },
]

describe('AccountFindings', () => {
  it('shows empty state when no findings', () => {
    render(<AccountFindings findings={[]} />)
    expect(screen.getByText('No findings')).toBeInTheDocument()
  })

  it('renders account names', () => {
    render(<AccountFindings findings={mockFindings} />)
    expect(screen.getByText('Production Account')).toBeInTheDocument()
    expect(screen.getByText('Staging Account')).toBeInTheDocument()
  })

  it('shows finding count per account', () => {
    render(<AccountFindings findings={mockFindings} />)
    expect(screen.getByText('2 findings')).toBeInTheDocument()
    expect(screen.getByText('1 finding')).toBeInTheDocument()
  })

  it('expands to show finding details on click', () => {
    render(<AccountFindings findings={mockFindings} />)
    const prodButton = screen.getByText('Production Account').closest('button')!
    fireEvent.click(prodButton)
    expect(screen.getByText('Unusual API activity detected')).toBeInTheDocument()
    expect(screen.getByText('CPU alarm triggered')).toBeInTheDocument()
  })

  it('collapses on second click', () => {
    render(<AccountFindings findings={mockFindings} />)
    const prodButton = screen.getByText('Production Account').closest('button')!
    fireEvent.click(prodButton)
    expect(screen.getByText('Unusual API activity detected')).toBeInTheDocument()
    fireEvent.click(prodButton)
    expect(screen.queryByText('Unusual API activity detected')).not.toBeInTheDocument()
  })
})
