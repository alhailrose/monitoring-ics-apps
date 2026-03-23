'use client'
// Client component — needs useState for expand/detail panel and search filter

import * as React from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { StatusBadge } from '@/components/common/StatusBadge'
import { SeverityBadge } from '@/components/common/SeverityBadge'
import { cn } from '@/lib/utils'
import { HugeiconsIcon } from '@hugeicons/react'
import {
  Alert01Icon,
  CheckmarkCircle01Icon,
  ArrowRight01Icon,
  Search01Icon,
} from '@hugeicons/core-free-icons'
import type { Finding, CheckResult, CheckStatus } from '@/lib/types/api'

interface AccountOverviewProps {
  findings: Finding[]
  results: CheckResult[]
  runName?: string
}

interface AccountData {
  accountId: string
  displayName: string
  findings: Finding[]
  results: CheckResult[]
  worstStatus: CheckStatus | null
  hasCritical: boolean
  hasHigh: boolean
}

const STATUS_ORDER: CheckStatus[] = ['ERROR', 'ALARM', 'WARN', 'NO_DATA', 'OK']

function worstOf(results: CheckResult[]): CheckStatus | null {
  if (results.length === 0) return null
  for (const s of STATUS_ORDER) {
    if (results.some((r) => r.status === s)) return s
  }
  return 'OK'
}

function buildAccountMap(findings: Finding[], results: CheckResult[]): AccountData[] {
  const map = new Map<string, AccountData>()

  for (const f of findings) {
    const key = f.account.id
    if (!map.has(key)) {
      map.set(key, { accountId: key, displayName: f.account.display_name, findings: [], results: [], worstStatus: null, hasCritical: false, hasHigh: false })
    }
    map.get(key)!.findings.push(f)
  }

  for (const r of results) {
    const key = r.account.id
    if (!map.has(key)) {
      map.set(key, { accountId: key, displayName: r.account.display_name, findings: [], results: [], worstStatus: null, hasCritical: false, hasHigh: false })
    }
    map.get(key)!.results.push(r)
  }

  return Array.from(map.values())
    .map((a) => ({
      ...a,
      worstStatus: worstOf(a.results),
      hasCritical: a.findings.some((f) => f.severity === 'CRITICAL'),
      hasHigh: a.findings.some((f) => f.severity === 'HIGH'),
    }))
    .filter((a) => a.findings.length > 0 || (a.worstStatus && a.worstStatus !== 'OK'))
    .sort((a, b) => {
      if (a.hasCritical !== b.hasCritical) return a.hasCritical ? -1 : 1
      if (a.hasHigh !== b.hasHigh) return a.hasHigh ? -1 : 1
      const ai = a.worstStatus ? STATUS_ORDER.indexOf(a.worstStatus) : 99
      const bi = b.worstStatus ? STATUS_ORDER.indexOf(b.worstStatus) : 99
      return ai - bi
    })
}

function DetailPanel({ account }: { account: AccountData }) {
  return (
    <div className="border-t border-border bg-muted/30 px-4 pb-4 pt-3 space-y-4">
      {account.findings.length > 0 && (
        <div>
          <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2">
            Findings ({account.findings.length})
          </p>
          <div className="space-y-1.5">
            {account.findings.map((f) => (
              <div key={f.id} className="flex items-start gap-3 rounded-md bg-background px-3 py-2 border border-border">
                <SeverityBadge severity={f.severity} className="mt-0.5 shrink-0" />
                <div className="min-w-0">
                  <p className="text-sm font-medium text-foreground truncate">{f.title}</p>
                  <p className="text-xs text-muted-foreground">{f.check_name}</p>
                  {f.description && (
                    <p className="text-xs text-muted-foreground mt-1 line-clamp-2">{f.description}</p>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {account.results.length > 0 && (
        <div>
          <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-2">
            Check Results ({account.results.length})
          </p>
          <div className="space-y-1.5">
            {account.results.map((r, i) => (
              <div key={i} className="flex items-start gap-3 rounded-md bg-background px-3 py-2 border border-border">
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
        </div>
      )}
    </div>
  )
}

function AccountRow({ account }: { account: AccountData }) {
  const [open, setOpen] = React.useState(false)

  const borderClass = account.hasCritical
    ? 'border-red-500/50 bg-red-500/5'
    : account.hasHigh
    ? 'border-orange-500/50 bg-orange-500/5'
    : account.worstStatus === 'ERROR' || account.worstStatus === 'ALARM'
    ? 'border-red-500/30 bg-red-500/5'
    : 'border-yellow-500/30 bg-yellow-500/5'

  const iconColor = account.hasCritical || account.worstStatus === 'ERROR' || account.worstStatus === 'ALARM'
    ? 'text-red-400'
    : 'text-yellow-400'

  const totalIssues = account.findings.length + account.results.filter(r => r.status !== 'OK').length

  return (
    <div className={cn('rounded-lg border transition-colors', borderClass)}>
      <div className="flex items-center justify-between gap-3 px-4 py-3">
        <div className="flex items-center gap-2 min-w-0">
          <HugeiconsIcon icon={Alert01Icon} strokeWidth={2} className={cn('size-4 shrink-0', iconColor)} />
          <span className="truncate text-sm font-medium text-foreground">{account.displayName}</span>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          {account.worstStatus && <StatusBadge status={account.worstStatus} />}
          {totalIssues > 0 && (
            <span className="rounded-full bg-muted px-1.5 py-0.5 text-[10px] font-medium text-muted-foreground">
              {totalIssues}
            </span>
          )}
          <Button
            variant="ghost"
            size="sm"
            onClick={() => setOpen((v) => !v)}
            className="h-7 px-2 text-xs"
          >
            Detail
            <HugeiconsIcon
              icon={ArrowRight01Icon}
              strokeWidth={2}
              className={cn('ml-1 size-3 transition-transform duration-200', open && 'rotate-90')}
            />
          </Button>
        </div>
      </div>

      {open && <DetailPanel account={account} />}
    </div>
  )
}

// Show threshold before search appears
const SEARCH_THRESHOLD = 5

export function AccountOverview({ findings, results, runName }: AccountOverviewProps) {
  const [search, setSearch] = React.useState('')
  const accounts = buildAccountMap(findings, results)

  const filtered = search.trim()
    ? accounts.filter((a) => a.displayName.toLowerCase().includes(search.toLowerCase()))
    : accounts

  const showSearch = accounts.length >= SEARCH_THRESHOLD

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-2 min-w-0">
            <CardTitle className="text-sm font-medium shrink-0">Account Overview</CardTitle>
            {runName && (
              <span className="text-xs text-muted-foreground truncate">· {runName}</span>
            )}
            {accounts.length > 0 && (
              <span className="rounded-full bg-muted px-1.5 py-0.5 text-[10px] font-medium text-muted-foreground shrink-0">
                {accounts.length} issue{accounts.length !== 1 ? 's' : ''}
              </span>
            )}
          </div>
          {showSearch && (
            <div className="relative w-44 shrink-0">
              <HugeiconsIcon
                icon={Search01Icon}
                strokeWidth={2}
                className="absolute left-2 top-1/2 -translate-y-1/2 size-3.5 text-muted-foreground pointer-events-none"
              />
              <Input
                placeholder="Filter accounts…"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="h-7 pl-7 text-xs"
              />
            </div>
          )}
        </div>
      </CardHeader>
      <CardContent>
        {accounts.length === 0 ? (
          <div className="flex items-center gap-2 rounded-lg border border-green-500/30 bg-green-500/5 px-4 py-3">
            <HugeiconsIcon icon={CheckmarkCircle01Icon} strokeWidth={2} className="size-4 text-green-400" />
            <span className="text-sm text-green-400 font-medium">All accounts are clean</span>
          </div>
        ) : filtered.length === 0 ? (
          <p className="text-sm text-muted-foreground text-center py-6">No accounts match &quot;{search}&quot;</p>
        ) : (
          <div className="space-y-2">
            {filtered.map((account) => (
              <AccountRow key={account.accountId} account={account} />
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
