'use client'
// Client component — needs useState for expand/collapse per account

import * as React from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { EmptyState } from '@/components/common/EmptyState'
import { SeverityBadge } from '@/components/common/SeverityBadge'
import { cn } from '@/lib/utils'
import { HugeiconsIcon } from '@hugeicons/react'
import { ArrowRight01Icon, Alert01Icon } from '@hugeicons/core-free-icons'
import type { Finding } from '@/lib/types/api'

interface AccountFindingsProps {
  findings: Finding[]
}

interface AccountGroup {
  accountId: string
  displayName: string
  findings: Finding[]
}

function groupByAccount(findings: Finding[]): AccountGroup[] {
  const map = new Map<string, AccountGroup>()
  for (const f of findings) {
    const key = f.account.id
    if (!map.has(key)) {
      map.set(key, { accountId: key, displayName: f.account.display_name, findings: [] })
    }
    map.get(key)!.findings.push(f)
  }
  // Sort by finding count descending
  return Array.from(map.values()).sort((a, b) => b.findings.length - a.findings.length)
}

function AccountRow({ group }: { group: AccountGroup }) {
  const [open, setOpen] = React.useState(false)

  const hasCritical = group.findings.some((f) => f.severity === 'CRITICAL')
  const hasHigh = group.findings.some((f) => f.severity === 'HIGH')
  const highlight = hasCritical ? 'border-red-500/40 bg-red-500/5' : hasHigh ? 'border-orange-500/40 bg-orange-500/5' : 'border-border'

  return (
    <div className={cn('rounded-lg border transition-colors', highlight)}>
      {/* Header row — clickable */}
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center justify-between gap-3 px-4 py-3 text-left"
      >
        <div className="flex items-center gap-2 min-w-0">
          <HugeiconsIcon icon={Alert01Icon} strokeWidth={2} className={cn('size-4 shrink-0', hasCritical ? 'text-red-400' : hasHigh ? 'text-orange-400' : 'text-yellow-400')} />
          <span className="truncate text-sm font-medium text-foreground">{group.displayName}</span>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          <span className="text-xs text-muted-foreground">{group.findings.length} finding{group.findings.length !== 1 ? 's' : ''}</span>
          <HugeiconsIcon
            icon={ArrowRight01Icon}
            strokeWidth={2}
            className={cn('size-4 text-muted-foreground transition-transform duration-200', open && 'rotate-90')}
          />
        </div>
      </button>

      {/* Expanded detail */}
      {open && (
        <div className="border-t border-border px-4 pb-3 pt-2 space-y-2">
          {group.findings.map((f) => (
            <div key={f.id} className="flex items-start gap-3 rounded-md bg-muted/40 px-3 py-2">
              <SeverityBadge severity={f.severity} className="mt-0.5 shrink-0" />
              <div className="min-w-0">
                <p className="text-sm font-medium text-foreground truncate">{f.title}</p>
                <p className="text-xs text-muted-foreground mt-0.5">{f.check_name}</p>
                {f.description && (
                  <p className="text-xs text-muted-foreground mt-1 line-clamp-2">{f.description}</p>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export function AccountFindings({ findings }: AccountFindingsProps) {
  const groups = groupByAccount(findings)

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm font-medium">Accounts with Findings</CardTitle>
      </CardHeader>
      <CardContent>
        {groups.length === 0 ? (
          <EmptyState
            title="No findings"
            description="All accounts are clean"
          />
        ) : (
          <div className="space-y-2">
            {groups.map((group) => (
              <AccountRow key={group.accountId} group={group} />
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
