import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { LoginForm } from '@/components/auth/LoginForm'

// Mock the server action
const mockLoginAction = jest.fn()
jest.mock('@/app/(auth)/login/actions', () => ({
  loginAction: (...args: unknown[]) => mockLoginAction(...args),
}))

// Mock next/navigation (used transitively)
jest.mock('next/navigation', () => ({
  redirect: jest.fn(),
  useSearchParams: () => new URLSearchParams(),
}))

describe('LoginForm', () => {
  beforeEach(() => {
    jest.clearAllMocks()
    mockLoginAction.mockResolvedValue(null)
  })

  it('renders username field', () => {
    render(<LoginForm />)
    expect(screen.getByLabelText(/username/i)).toBeInTheDocument()
  })

  it('renders password field', () => {
    render(<LoginForm />)
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument()
  })

  it('renders submit button', () => {
    render(<LoginForm />)
    expect(screen.getByRole('button', { name: /login/i })).toBeInTheDocument()
  })

  it('renders enterprise helper text', () => {
    render(<LoginForm />)
    expect(screen.getByText(/ruang kendali ics/i)).toBeInTheDocument()
    expect(screen.getByText(/aktivitas login dipantau/i)).toBeInTheDocument()
  })

  it('shows error alert when action returns an error', async () => {
    mockLoginAction.mockResolvedValue({ error: 'Invalid username or password' })

    render(<LoginForm />)

    await userEvent.type(screen.getByLabelText(/username/i), 'admin')
    await userEvent.type(screen.getByLabelText(/password/i), 'wrong')
    await userEvent.click(screen.getByRole('button', { name: /login/i }))

    expect(await screen.findByRole('alert')).toBeInTheDocument()
    expect(await screen.findByText('Invalid username or password')).toBeInTheDocument()
  })
})
