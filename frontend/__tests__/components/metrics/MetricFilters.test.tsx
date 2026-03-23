import React from 'react'
import { render, screen } from '@testing-library/react'
import { MetricFilters } from '@/components/metrics/MetricFilters'

jest.mock('next/navigation', () => ({
  useRouter: () => ({ push: jest.fn() }),
  useSearchParams: () => new URLSearchParams(),
  usePathname: () => '/metrics',
}))

describe('MetricFilters', () => {
  it('renders status select', () => {
    render(<MetricFilters customerId="cust-1" />)
    expect(screen.getByLabelText('Filter by status')).toBeInTheDocument()
  })

  it('renders check select', () => {
    render(<MetricFilters customerId="cust-1" />)
    expect(screen.getByLabelText('Filter by check')).toBeInTheDocument()
  })
})
