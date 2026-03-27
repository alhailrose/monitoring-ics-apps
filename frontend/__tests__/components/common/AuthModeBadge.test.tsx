import { render, screen } from '@testing-library/react'
import { AuthModeBadge } from '@/components/common/AuthModeBadge'

describe('AuthModeBadge', () => {
  const modes = ['profile', 'access_key', 'assumed_role'] as const

  modes.forEach((mode) => {
    it(`renders ${mode}`, () => {
      render(<AuthModeBadge mode={mode} />)
      expect(screen.getByRole('generic')).toBeInTheDocument()
    })
  })
})
