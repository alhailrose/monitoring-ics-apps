'use client'

import { usePathname } from 'next/navigation'
import Link from 'next/link'
import { HugeiconsIcon } from '@hugeicons/react'
import { ArrowRight01Icon } from '@hugeicons/core-free-icons'

const SEGMENT_LABELS: Record<string, string> = {
  dashboard: 'Dashboard',
  customers: 'Customers',
  history: 'History',
  findings: 'Findings',
  metrics: 'Metrics',
  reports: 'Reports',
  ticketing: 'Ticketing',
  mailing: 'Mailing',
  tasks: 'Tasks',
  checks: 'Checks',
  alarms: 'Alarms',
  settings: 'Settings',
  users: 'Users',
  invites: 'Invites',
  'aws-config': 'AWS Config',
  'my-config': 'My Config',
  terminal: 'Terminal',
  arbel: 'Arbel',
  bundled: 'Bundled',
  dedicated: 'Dedicated',
  specific: 'Specific',
}

function labelFor(segment: string): string {
  // UUID-like segment → show as short ID
  if (/^[0-9a-f-]{32,}$/i.test(segment)) return segment.slice(0, 8) + '…'
  return SEGMENT_LABELS[segment] ?? segment.replace(/-/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
}

export function Breadcrumb() {
  const pathname = usePathname()
  const segments = pathname.split('/').filter(Boolean)

  if (segments.length <= 1) return null

  const crumbs = segments.map((seg, i) => ({
    label: labelFor(seg),
    href: '/' + segments.slice(0, i + 1).join('/'),
    isLast: i === segments.length - 1,
  }))

  return (
    <nav aria-label="Breadcrumb" className="flex items-center gap-1 text-sm">
      {crumbs.map((crumb, i) => (
        <span key={crumb.href} className="flex items-center gap-1">
          {i > 0 && (
            <HugeiconsIcon
              icon={ArrowRight01Icon}
              className="h-3 w-3 text-muted-foreground/50 shrink-0"
            />
          )}
          {crumb.isLast ? (
            <span className="font-medium text-foreground truncate max-w-[180px]">
              {crumb.label}
            </span>
          ) : (
            <Link
              href={crumb.href}
              className="text-muted-foreground hover:text-foreground transition-colors truncate max-w-[120px]"
            >
              {crumb.label}
            </Link>
          )}
        </span>
      ))}
    </nav>
  )
}
