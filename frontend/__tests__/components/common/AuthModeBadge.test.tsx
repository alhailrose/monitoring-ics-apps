import { render, screen } from '@testing-library/react'
import { AuthModeBadge } from '@/components/common/AuthModeBadge'

describe('AuthModeBadge', () => {
  const modes = ['assume_role', 'sso', 'aws_login', 'access_key'] as const

  modes.forEach((mode) => {
    it(`renders ${mode}`, () => {
      render(<AuthModeBadge mode={mode} />)
      expect(screen.getByText(mode)).toBeInTheDocument()
    })
  })
})
