import React from 'react'
import { render, screen } from '@testing-library/react'
import { FindingsTable } from '@/components/findings/FindingsTable'
import type { Finding } from '@/lib/types/api'

jest.mock('next/navigation', () => ({
  useRouter: () => ({ push: jest.fn() }),
  useSearchParams: () => new URLSearchParams(),
  usePathname: () => '/findings',
}))

const mockFinding = (overrides: Partial<Finding> = {}): Finding => ({
  id: 'f-1',
  check_run_id: 'run-1',
  account: { id: 'acc-1', profile_name: 'prod', display_name: 'Production' },
  check_name: 'guardduty',
  finding_key: 'key-1',
  severity: 'HIGH',
  title: 'Suspicious activity detected',
  description: 'Some description',
  created_at: '2026-03-22T10:00:00Z',
  ...overrides,
})

describe('FindingsTable', () => {
  it('renders finding rows', () => {
    render(
      <FindingsTable
        findings={[mockFinding(), mockFinding({ id: 'f-2', title: 'Another finding' })]}
        total={2}
        page={1}
        pageSize={20}
      />,
    )
    expect(screen.getByText('Suspicious activity detected')).toBeInTheDocument()
    expect(screen.getByText('Another finding')).toBeInTheDocument()
  })

  it('shows EmptyState when findings array is empty', () => {
    render(<FindingsTable findings={[]} total={0} page={1} pageSize={20} />)
    expect(screen.getByText('No findings')).toBeInTheDocument()
    expect(screen.getByText('All checks are clean')).toBeInTheDocument()
  })

  it('renders severity badge', () => {
    render(
      <FindingsTable
        findings={[mockFinding({ severity: 'CRITICAL' })]}
        total={1}
        page={1}
        pageSize={20}
      />,
    )
    expect(screen.getByText('CRITICAL')).toBeInTheDocument()
  })

  it('renders account display name', () => {
    render(
      <FindingsTable
        findings={[mockFinding()]}
        total={1}
        page={1}
        pageSize={20}
      />,
    )
    expect(screen.getByText('Production')).toBeInTheDocument()
  })

  it('shows when a finding was first detected', () => {
    render(
      <FindingsTable
        findings={[mockFinding({ last_seen_at: '2026-03-23T10:00:00Z' })]}
        total={1}
        page={1}
        pageSize={20}
      />,
    )
    expect(screen.getByText(/found/i)).toBeInTheDocument()
  })
})
