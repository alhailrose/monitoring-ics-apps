import { render, screen } from '@testing-library/react'
import { CheckDetailView } from '@/components/checks/CheckDetailView'

describe('CheckDetailView', () => {
  it('renders arbel metric detail messages for warn states', () => {
    render(
      <CheckDetailView
        checkName="daily-arbel-rds"
        details={{
          window_hours: 12,
          service_type: 'rds',
          instances: {
            writer: {
              instance_id: 'noncis-prod-rds-instance-1',
              metrics: {
                ACUUtilization: {
                  avg: 25.52,
                  status: 'past-warn',
                  message:
                    'ACU Utilization: 25% (sekarang normal, sempat > 75% | 100% pukul 06:28-06:35 WIB (8 menit))',
                },
                CPUUtilization: {
                  avg: 10.61,
                  status: 'ok',
                  message: 'CPU Utilization: 11% (normal)',
                },
              },
            },
          },
        }}
      />,
    )

    expect(screen.getByText('Window: 12h · Type: RDS')).toBeInTheDocument()
    expect(screen.getByText('Details')).toBeInTheDocument()
    expect(
      screen.getByText(/sekarang normal, sempat > 75%/i),
    ).toBeInTheDocument()
  })
})
