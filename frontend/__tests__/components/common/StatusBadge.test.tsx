import { render, screen } from '@testing-library/react'
import { StatusBadge } from '@/components/common/StatusBadge'

describe('StatusBadge', () => {
  const statuses = ['OK', 'WARN', 'ERROR', 'ALARM', 'NO_DATA'] as const

  statuses.forEach((status) => {
    it(`renders ${status}`, () => {
      render(<StatusBadge status={status} />)
      expect(screen.getByText(status)).toBeInTheDocument()
    })
  })
})
