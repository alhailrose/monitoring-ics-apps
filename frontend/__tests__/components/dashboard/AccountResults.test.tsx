import { render, screen, fireEvent } from '@testing-library/react'
import { AccountResults } from '@/components/dashboard/AccountResults'
import type { CheckResult } from '@/lib/types/api'

const mockResults: CheckResult[] = [
  {
    customer_id: 'cust-1',
    account: { id: 'acc-1', profile_name: 'prod', display_name: 'Production Account' },
    check_name: 'guardduty',
    status: 'ERROR',
    summary: 'GuardDuty findings detected',
    output: '',
  },
  {
    customer_id: 'cust-1',
    account: { id: 'acc-1', profile_name: 'prod', display_name: 'Production Account' },
    check_name: 'cloudwatch_alarms',
    status: 'WARN',
    summary: 'Some alarms in ALARM state',
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

describe('AccountResults', () => {
  it('shows empty state when no results', () => {
    render(<AccountResults results={[]} />)
    expect(screen.getByText('No results')).toBeInTheDocument()
  })

  it('renders account names', () => {
    render(<AccountResults results={mockResults} />)
    expect(screen.getByText('Production Account')).toBeInTheDocument()
    expect(screen.getByText('Staging Account')).toBeInTheDocument()
  })

  it('shows run name when provided', () => {
    render(<AccountResults results={mockResults} runName="guardduty" />)
    expect(screen.getByText(/guardduty/)).toBeInTheDocument()
  })

  it('expands non-clean accounts on click', () => {
    render(<AccountResults results={mockResults} />)
    const prodButton = screen.getByText('Production Account').closest('button')!
    fireEvent.click(prodButton)
    expect(screen.getByText('GuardDuty findings detected')).toBeInTheDocument()
  })

  it('clean accounts are shown without expand button', () => {
    render(<AccountResults results={mockResults} />)
    // Staging is OK — no button wrapper
    const stagingEl = screen.getByText('Staging Account')
    expect(stagingEl.closest('button')).toBeNull()
  })
})
