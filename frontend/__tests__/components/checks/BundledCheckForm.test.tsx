import { render, screen } from '@testing-library/react'
import { BundledCheckForm } from '@/components/checks/BundledCheckForm'
import type { Customer } from '@/lib/types/api'

jest.mock('@/app/(dashboard)/checks/actions', () => ({
  runChecks: jest.fn(),
}))

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
    slack_enabled: false,
    slack_channel: null,
    report_mode: 'summary',
    label: null,
    accounts: [],
  },
]

describe('BundledCheckForm', () => {
  it('renders mode select', () => {
    render(<BundledCheckForm customers={mockCustomers} />)
    expect(screen.getByLabelText('Mode')).toBeInTheDocument()
  })

  it('shows all and arbel options in mode select', () => {
    render(<BundledCheckForm customers={mockCustomers} />)
    expect(screen.getAllByText('All Checks').length).toBeGreaterThan(0)
    expect(screen.getByText('Arbel Suite')).toBeInTheDocument()
  })

  it('renders customer toggle buttons', () => {
    render(<BundledCheckForm customers={mockCustomers} />)
    expect(screen.getByRole('button', { name: /acme corp/i })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /beta inc/i })).toBeInTheDocument()
  })

  it('run button is disabled when no customer selected', () => {
    render(<BundledCheckForm customers={mockCustomers} />)
    expect(screen.getByRole('button', { name: /run checks/i })).toBeDisabled()
  })

  it('renders with empty customers list', () => {
    render(<BundledCheckForm customers={[]} />)
    expect(screen.getByRole('button', { name: /run checks/i })).toBeInTheDocument()
  })
})
