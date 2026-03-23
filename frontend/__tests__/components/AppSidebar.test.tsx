import React from 'react'
import { render, screen } from '@testing-library/react'
import { AppSidebar } from '@/components/app-sidebar'
import { SidebarProvider } from '@/components/ui/sidebar'
import { TerminalProvider } from '@/components/terminal/TerminalContext'

jest.mock('next/navigation', () => ({
  usePathname: () => '/dashboard',
  useRouter: () => ({ push: jest.fn() }),
}))

jest.mock('@/app/(dashboard)/logout/actions', () => ({
  logoutAction: jest.fn(),
}))

function renderSidebar(role: 'super_user' | 'user' = 'super_user') {
  return render(
    <TerminalProvider>
      <SidebarProvider>
        <AppSidebar user={{ username: 'admin', role }} />
      </SidebarProvider>
    </TerminalProvider>
  )
}

describe('AppSidebar', () => {
  it('renders all nav items', () => {
    renderSidebar()
    expect(screen.getByText('Dashboard')).toBeInTheDocument()
    expect(screen.getByText('Customers')).toBeInTheDocument()
    expect(screen.getByText('History')).toBeInTheDocument()
    expect(screen.getByText('Findings')).toBeInTheDocument()
    expect(screen.getByText('Metrics')).toBeInTheDocument()
  })

  it('marks Dashboard as active when pathname is /dashboard', () => {
    renderSidebar()
    const dashboardLink = screen.getByText('Dashboard').closest('a')
    expect(dashboardLink?.closest('[data-active="true"]')).toBeInTheDocument()
  })

  it('displays the username', () => {
    renderSidebar()
    expect(screen.getAllByText('admin').length).toBeGreaterThan(0)
  })
})
