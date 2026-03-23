import { render, screen } from '@testing-library/react'
import { PageHeader } from '@/components/common/PageHeader'

describe('PageHeader', () => {
  it('renders title', () => {
    render(<PageHeader title="Customers" />)
    expect(screen.getByText('Customers')).toBeInTheDocument()
  })

  it('renders actions when provided', () => {
    render(<PageHeader title="Customers" actions={<button>Add</button>} />)
    expect(screen.getByRole('button', { name: 'Add' })).toBeInTheDocument()
  })

  it('does not render actions slot when omitted', () => {
    render(<PageHeader title="Customers" />)
    expect(screen.queryByRole('button')).not.toBeInTheDocument()
  })
})
