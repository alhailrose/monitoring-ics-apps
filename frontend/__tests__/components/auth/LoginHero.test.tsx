import { render, screen } from '@testing-library/react'
import { LoginHero } from '@/components/auth/LoginHero'

describe('LoginHero', () => {
  it('shows hero copy and footer credit', () => {
    render(<LoginHero />)
    expect(screen.getByText(/Infrastructure Command Suite/i)).toBeInTheDocument()
    expect(
      screen.getByText(/Operational visibility for multi-region workloads/i)
    ).toBeInTheDocument()
    expect(screen.getByText(/Made by Bagus Ganteng 😎/i)).toBeInTheDocument()
  })
})
