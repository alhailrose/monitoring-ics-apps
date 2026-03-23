import { render, screen } from '@testing-library/react'
import { EmptyState } from '@/components/common/EmptyState'

describe('EmptyState', () => {
  it('renders title', () => {
    render(<EmptyState title="No data found" />)
    expect(screen.getByText('No data found')).toBeInTheDocument()
  })

  it('renders description when provided', () => {
    render(<EmptyState title="No data" description="Try adjusting your filters." />)
    expect(screen.getByText('Try adjusting your filters.')).toBeInTheDocument()
  })

  it('does not render description when omitted', () => {
    render(<EmptyState title="No data" />)
    expect(screen.queryByText('Try adjusting your filters.')).not.toBeInTheDocument()
  })
})
