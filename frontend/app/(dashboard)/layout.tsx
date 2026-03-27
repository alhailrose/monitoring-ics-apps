import { redirect } from 'next/navigation'
import { getSession } from '@/lib/auth'
import { AppSidebar } from '@/components/app-sidebar'
import { SidebarInset, SidebarProvider, SidebarTrigger } from '@/components/ui/sidebar'
import { Separator } from '@/components/ui/separator'
import { AuthProvider } from '@/components/providers/AuthProvider'
import { TerminalProvider } from '@/components/terminal/TerminalContext'
import { TerminalDrawer } from '@/components/terminal/TerminalDrawer'
import { TerminalToggleButton } from '@/components/terminal/TerminalToggleButton'

export default async function DashboardLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const session = await getSession()
  if (!session) redirect('/login')

  const headerBar = (
    <header className="sticky top-0 z-10 flex h-12 shrink-0 items-center justify-between border-b bg-background px-4">
      <div className="flex items-center gap-2">
        <SidebarTrigger className="-ml-1" />
        <Separator orientation="vertical" className="h-4" />
      </div>
      <div className="flex items-center gap-1">
        <TerminalToggleButton />
      </div>
    </header>
  )

  return (
    <AuthProvider>
      <SidebarProvider className="!h-svh overflow-x-hidden">
        <TerminalProvider>
          <AppSidebar user={{ username: session.username, role: session.role }} />
          <SidebarInset className="flex min-h-0 min-w-0 flex-col overflow-hidden">
            {headerBar}
            <main className="flex-1 overflow-y-auto">{children}</main>
          </SidebarInset>
          <TerminalDrawer />
        </TerminalProvider>
      </SidebarProvider>
    </AuthProvider>
  )
}
