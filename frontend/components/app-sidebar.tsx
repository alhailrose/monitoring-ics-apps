"use client"

import * as React from "react"
import Link from "next/link"
import { usePathname } from "next/navigation"
import { NavUser } from "@/components/nav-user"
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarSeparator,
} from "@/components/ui/sidebar"
import { HugeiconsIcon } from "@hugeicons/react"
import {
  DashboardBrowsingIcon,
  UserAccountIcon,
  Clock01Icon,
  Alert01Icon,
  Chart01Icon,
  CheckListIcon,
  MonitorDotIcon,
  TaskIcon,
  UserSettings01Icon,
  Mail01Icon,
  Terminal01Icon,
} from "@hugeicons/core-free-icons"
import { cn } from "@/lib/utils"
import type { UserRole } from "@/lib/types/api"

// Terminal toggle button removed from sidebar — now lives in the top header bar

const navItems = [
  { title: "Dashboard", url: "/dashboard", icon: DashboardBrowsingIcon },
  { title: "Customers", url: "/customers", icon: UserAccountIcon },
  { title: "History", url: "/history", icon: Clock01Icon },
  { title: "Findings", url: "/findings", icon: Alert01Icon },
  { title: "Metrics", url: "/metrics", icon: Chart01Icon },
  { title: "Reports", url: "/reports", icon: TaskIcon },
]

const opsItems = [
  { title: "Tasks", url: "/tasks", icon: TaskIcon },
  { title: "Checks", url: "/checks", icon: CheckListIcon },
]

interface AppSidebarProps extends React.ComponentProps<typeof Sidebar> {
  user: { username: string; role: UserRole }
}

export function AppSidebar({ user, ...props }: AppSidebarProps) {
  const pathname = usePathname()

  return (
    <Sidebar collapsible="icon" {...props}>
      {/* Branded header */}
      <SidebarHeader className="border-b border-sidebar-border pb-3">
        <div className="flex items-center gap-3 px-2 py-1">
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-sidebar-primary text-sidebar-primary-foreground shadow-md">
            <HugeiconsIcon icon={MonitorDotIcon} strokeWidth={2} className="size-4" />
          </div>
          <div className="grid flex-1 leading-tight group-data-[collapsible=icon]:hidden">
            <span className="truncate font-bold text-sm text-sidebar-foreground">ICS Monitor</span>
            <span className="truncate text-[10px] text-sidebar-foreground/50 uppercase tracking-widest">Cloud Platform</span>
          </div>
        </div>
      </SidebarHeader>

      <SidebarContent className="pt-2">
        <SidebarGroup>
          <SidebarGroupLabel className="text-sidebar-foreground/40 uppercase tracking-widest text-[10px]">
            Main
          </SidebarGroupLabel>
          <SidebarMenu>
            {navItems.map((item) => {
              const isActive = pathname.startsWith(item.url)
              return (
                <SidebarMenuItem key={item.title}>
                  <SidebarMenuButton
                    asChild
                    isActive={isActive}
                    tooltip={item.title}
                    className={cn(
                      isActive && "bg-sidebar-primary/20 text-sidebar-primary font-medium border-l-2 border-sidebar-primary rounded-l-none"
                    )}
                  >
                    <Link href={item.url}>
                      <HugeiconsIcon icon={item.icon} strokeWidth={2} />
                      <span>{item.title}</span>
                    </Link>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              )
            })}
          </SidebarMenu>
        </SidebarGroup>

        <SidebarSeparator />

        <SidebarGroup>
          <SidebarGroupLabel className="text-sidebar-foreground/40 uppercase tracking-widest text-[10px]">
            Operations
          </SidebarGroupLabel>
          <SidebarMenu>
            {opsItems.map((item) => {
              const isActive = pathname.startsWith(item.url)
              return (
                <SidebarMenuItem key={item.title}>
                  <SidebarMenuButton
                    asChild
                    isActive={isActive}
                    tooltip={item.title}
                    className={cn(
                      isActive && "bg-sidebar-primary/20 text-sidebar-primary font-medium border-l-2 border-sidebar-primary rounded-l-none"
                    )}
                  >
                    <Link href={item.url}>
                      <HugeiconsIcon icon={item.icon} strokeWidth={2} />
                      <span>{item.title}</span>
                    </Link>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              )
            })}
          </SidebarMenu>
        </SidebarGroup>

        {/* Settings — only visible to super_user */}
        {user.role === 'super_user' && (
          <>
            <SidebarSeparator />
            <SidebarGroup>
              <SidebarGroupLabel className="text-sidebar-foreground/40 uppercase tracking-widest text-[10px]">
                Settings
              </SidebarGroupLabel>
              <SidebarMenu>
                <SidebarMenuItem>
                  <SidebarMenuButton
                    asChild
                    isActive={pathname.startsWith('/settings/users')}
                    tooltip="User Management"
                    className={cn(
                      pathname.startsWith('/settings/users') && "bg-sidebar-primary/20 text-sidebar-primary font-medium border-l-2 border-sidebar-primary rounded-l-none"
                    )}
                  >
                    <Link href="/settings/users">
                      <HugeiconsIcon icon={UserSettings01Icon} strokeWidth={2} />
                      <span>Users</span>
                    </Link>
                  </SidebarMenuButton>
                </SidebarMenuItem>
                <SidebarMenuItem>
                  <SidebarMenuButton
                    asChild
                    isActive={pathname.startsWith('/settings/invites')}
                    tooltip="Undangan"
                    className={cn(
                      pathname.startsWith('/settings/invites') && "bg-sidebar-primary/20 text-sidebar-primary font-medium border-l-2 border-sidebar-primary rounded-l-none"
                    )}
                  >
                    <Link href="/settings/invites">
                      <HugeiconsIcon icon={Mail01Icon} strokeWidth={2} />
                      <span>Invites</span>
                    </Link>
                  </SidebarMenuButton>
                </SidebarMenuItem>
                <SidebarMenuItem>
                  <SidebarMenuButton
                    asChild
                    isActive={pathname.startsWith('/settings/aws-config')}
                    tooltip="AWS Config Template"
                    className={cn(
                      pathname.startsWith('/settings/aws-config') && "bg-sidebar-primary/20 text-sidebar-primary font-medium border-l-2 border-sidebar-primary rounded-l-none"
                    )}
                  >
                    <Link href="/settings/aws-config">
                      <HugeiconsIcon icon={Terminal01Icon} strokeWidth={2} />
                      <span>AWS Config</span>
                    </Link>
                  </SidebarMenuButton>
                </SidebarMenuItem>
              </SidebarMenu>
            </SidebarGroup>
          </>
        )}
      </SidebarContent>

      <SidebarFooter className="border-t border-sidebar-border pt-2">
        <NavUser user={user} />
      </SidebarFooter>
    </Sidebar>
  )
}
