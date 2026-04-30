import { render, screen } from '@testing-library/react'
import { AuthModeBadge } from '@/components/common/AuthModeBadge'

describe('AuthModeBadge', () => {
  const cases = [
    { mode: 'profile' as const, label: 'Profile' },
    { mode: 'access_key' as const, label: 'Access Key' },
    { mode: 'assumed_role' as const, label: 'Assumed Role' },
  ]

  cases.forEach(({ mode, label }) => {
    it(`renders ${mode}`, () => {
      render(<AuthModeBadge mode={mode} />)
      expect(screen.getByText(label)).toBeInTheDocument()
    })
  })
})
