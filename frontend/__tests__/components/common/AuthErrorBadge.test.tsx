import { render, screen } from '@testing-library/react'
import { AuthErrorBadge } from '@/components/common/AuthErrorBadge'

Object.assign(navigator, { clipboard: { writeText: jest.fn() } })

describe('AuthErrorBadge', () => {
  it('renders nothing when errorClass is null', () => {
    const { container } = render(<AuthErrorBadge errorClass={null} />)
    expect(container).toBeEmptyDOMElement()
  })

  it('renders label for sso_expired', () => {
    render(<AuthErrorBadge errorClass="sso_expired" />)
    expect(screen.getByText('Login required')).toBeInTheDocument()
  })

  it('renders label for assume_role_failed', () => {
    render(<AuthErrorBadge errorClass="assume_role_failed" />)
    expect(screen.getByText('Access denied')).toBeInTheDocument()
  })

  it('renders label for invalid_credentials', () => {
    render(<AuthErrorBadge errorClass="invalid_credentials" />)
    expect(screen.getByText('Invalid credentials')).toBeInTheDocument()
  })

  it('renders label for no_config', () => {
    render(<AuthErrorBadge errorClass="no_config" />)
    expect(screen.getByText('Not configured')).toBeInTheDocument()
  })

  it('renders loginCommand text when provided', () => {
    render(<AuthErrorBadge errorClass="sso_expired" loginCommand="aws sso login --profile dev" />)
    expect(screen.getByText('Login required')).toBeInTheDocument()
    // When loginCommand is provided, the badge is wrapped in a tooltip trigger
    expect(screen.getByText('Login required').closest('[data-slot="tooltip-trigger"]')).toBeInTheDocument()
  })
})
