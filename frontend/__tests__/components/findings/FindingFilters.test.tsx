import React from 'react'
import { render, screen } from '@testing-library/react'
import { FindingFilters } from '@/components/findings/FindingFilters'

jest.mock('next/navigation', () => ({
  useRouter: () => ({ push: jest.fn() }),
  useSearchParams: () => new URLSearchParams(),
  usePathname: () => '/findings',
}))

describe('FindingFilters', () => {
  it('renders severity select', () => {
    render(<FindingFilters customerId="cust-1" />)
    expect(screen.getByRole('combobox', { name: /severity/i })).toBeInTheDocument()
  })

  it('renders check select', () => {
    render(<FindingFilters customerId="cust-1" />)
    expect(screen.getByRole('combobox', { name: /check/i })).toBeInTheDocument()
  })
})
