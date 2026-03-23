/**
 * @jest-environment jsdom
 */
import React from 'react'
import { render, screen } from '@testing-library/react'
import { TopChecksTable } from '@/components/dashboard/TopChecksTable'

describe('TopChecksTable', () => {
  it('renders EmptyState when checks array is empty', () => {
    render(<TopChecksTable checks={[]} />)
    expect(screen.getByText('No checks run yet')).toBeInTheDocument()
    expect(screen.getByText('Run a check to see activity here')).toBeInTheDocument()
  })

  it('renders check names when data is provided', () => {
    const checks = [
      { check_name: 'ec2_list', runs: 5 },
      { check_name: 'guardduty', runs: 3 },
    ]
    render(<TopChecksTable checks={checks} />)
    expect(screen.getByText('ec2_list')).toBeInTheDocument()
    expect(screen.getByText('guardduty')).toBeInTheDocument()
    expect(screen.getByText('5 runs')).toBeInTheDocument()
    expect(screen.getByText('3 runs')).toBeInTheDocument()
  })

  it('uses singular "run" for count of 1', () => {
    render(<TopChecksTable checks={[{ check_name: 'backup_status', runs: 1 }]} />)
    expect(screen.getByText('1 run')).toBeInTheDocument()
  })
})
