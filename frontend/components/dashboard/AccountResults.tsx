'use client'
// Client component — needs useState for expand/collapse per account

import * as React from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { EmptyState } from '@/components/common/EmptyState'
import { StatusBadge } from '@/components/common/StatusBadge'
import { cn } from '@/lib/utils'
import { HugeiconsIcon } from '@hugeicons/react'
import { ArrowRight01Icon } from '@hugeicons/core-free-icons'
import type { CheckResult, CheckStatus } from '@/lib/types/api'

interface AccountResultsProps {
  results: CheckResult[]
  runName?: string
}

interface AccountGroup {
  accountId: string
  displayName: string
  results: CheckResult[]
  worstStatus: CheckStatus
}

const STATUS_ORDER: CheckStatus[] = ['ERROR', 'ALARM', 'WARN', 'NO_DATA', 'OK']

function worstOf(results: CheckResult[]): CheckStatus {
  for (const s of STATUS_ORDER) {
    if (results.some((r) => r.status === s)) return s
  }
  return 'OK'
}

function groupByAccount(results: CheckResult[]): AccountGroup[] {
  const map = new Map<string, AccountGroup>()
  for (const r of results) {
    const key = r.account.id
    if (!map.has(key)) {
      map.set(key, { accountId: key, displayName: r.account.display_name, results: [], worstStatus: 'OK' })
    }
    map.get(key)!.results.push(r)
  }
  const groups = Array.from(map.values()).map((g) => ({ ...g, worstStatus: worstOf(g.results) }))
  // Sort: worst first, then OK
  return groups.sort((a, b) => STATUS_ORDER.indexOf(a.worstStatus) - STATUS_ORDER.indexOf(b.worstStatus))
}

const HIGHLIGHT: Partial<Record<CheckStatus, string>> = {
  ERROR: 'border-red-500/40 bg-red-500/5',
  ALARM: 'border-red-500/40 bg-red-500/5',
  WARN:  'border-yellow-500/40 bg-yellow-500/5',
}

function AccountRow({ group }: { group: AccountGroup }) {
  const [open, setOpen] = React.useState(false)
  const borderClass = HIGHLIGHT[group.worstStatus] ?? 'border-border'
  const isClean = group.worstStatus === 'OK'

  if (isClean) {
    // Clean accounts — show compact, no expand needed
    return (
      <div className="flex items-center justify-between rounded-lg border border-border px-4 py-2.5">
        <span className="text-sm text-muted-foreground truncate">{group.displayName}</span>
        <StatusBadge status="OK" />
      </div>
    )
  }

  return (
    <div className={cn('rounded-lg border transition-colors', borderClass)}>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center justify-between gap-3 px-4 py-3 text-left"
      >
        <div className="flex items-center gap-2 min-w-0">
          <StatusBadge status={group.worstStatus} />
          <span className="truncate text-sm font-medium text-foreground">{group.displayName}</span>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          <span className="text-xs text-muted-foreground">{group.results.length} result{group.results.length !== 1 ? 's' : ''}</span>
          <HugeiconsIcon
            icon={ArrowRight01Icon}
            strokeWidth={2}
            className={cn('size-4 text-muted-foreground transition-transform duration-200', open && 'rotate-90')}
          />
        </div>
      </button>

      {open && (
        <div className="border-t border-border px-4 pb-3 pt-2 space-y-1.5">
          {group.results.map((r, i) => (
            <div key={i} className="flex items-start gap-3 rounded-md bg-muted/40 px-3 py-2">
              <StatusBadge status={r.status} />
              <div className="min-w-0">
                <p className="text-sm font-medium text-foreground truncate">{r.check_name}</p>
                {r.summary && (
                  <p className="text-xs text-muted-foreground mt-0.5 line-clamp-2">{r.summary}</p>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export function AccountResults({ results, runName }: AccountResultsProps) {
  const groups = groupByAccount(results)

  return (
    <Card>
      <CardHeader>
        <div>
          <CardTitle className="text-sm font-medium">Account Results</CardTitle>
          {runName && (
            <p className="text-xs text-muted-foreground mt-0.5">From: {runName}</p>
          )}
        </div>
      </CardHeader>
      <CardContent>
        {groups.length === 0 ? (
          <EmptyState
            title="No results"
            description="Run a check to see account results here"
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
