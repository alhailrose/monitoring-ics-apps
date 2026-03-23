import { render, screen } from '@testing-library/react'
import { SeverityBadge } from '@/components/common/SeverityBadge'

describe('SeverityBadge', () => {
  const severities = ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'INFO', 'ALARM'] as const

  severities.forEach((severity) => {
    it(`renders ${severity}`, () => {
      render(<SeverityBadge severity={severity} />)
      expect(screen.getByText(severity)).toBeInTheDocument()
    })
  })
})
