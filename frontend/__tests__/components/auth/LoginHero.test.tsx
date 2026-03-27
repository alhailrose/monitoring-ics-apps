import { render, screen } from '@testing-library/react'
import { LoginHero } from '@/components/auth/LoginHero'

describe('LoginHero', () => {
  it('renders hero strip, stats, and footer layout hooks', () => {
    render(<LoginHero />)
    const strip = screen.getByTestId('login-hero-strip')
    expect(strip).toHaveClass('rounded-full')
    expect(screen.getByText(/99.95% uptime/i)).toBeInTheDocument()
    expect(screen.getByText(/Made by Bagus Ganteng 😎/i)).toBeInTheDocument()
  })
})
