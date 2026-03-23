import { render, screen } from '@testing-library/react'
import { CheckProgress } from '@/components/checks/CheckProgress'

describe('CheckProgress', () => {
  it('renders with default label', () => {
    render(<CheckProgress />)
    expect(screen.getByText('Running checks')).toBeInTheDocument()
  })

  it('renders with custom label', () => {
    render(<CheckProgress label="Running Arbel Check…" />)
    expect(screen.getByText('Running Arbel Check…')).toBeInTheDocument()
  })

  it('shows initial step text', () => {
    render(<CheckProgress />)
    expect(screen.getByText('Preparing check execution…')).toBeInTheDocument()
  })

  it('shows elapsed time counter', () => {
    render(<CheckProgress />)
    expect(screen.getByText('0s')).toBeInTheDocument()
  })
})
