'use client'

import { useState, useTransition } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { toast } from 'sonner'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { SeverityBadge } from '@/components/common/SeverityBadge'
import { AuthModeBadge } from '@/components/common/AuthModeBadge'
import { AccountSheet } from '@/components/customers/AccountSheet'
import { useSessionsHealth } from '@/components/customers/useSessionsHealth'
import { deleteAccount } from '@/app/(dashboard)/customers/actions'
import { HugeiconsIcon } from '@hugeicons/react'
import {
  UserAccountIcon,
  Alert01Icon,
  Clock01Icon,
  CheckmarkBadge01Icon,
  ArrowRight01Icon,
  LinkSquare01Icon,
  Add01Icon,
} from '@hugeicons/core-free-icons'
import { cn, formatDateFull } from '@/lib/utils'
import type { Customer, Finding, CheckRunSummary, SessionStatus, Account, UserRole } from '@/lib/types/api'

// ── sub-components ────────────────────────────────────────────────────────────

function sessionBadgeClass(status: SessionStatus): string {
  if (status === 'ok') return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
  if (status === 'expired') return 'bg-red-500/10 text-red-400 border-red-500/20'
  if (status === 'error') return 'bg-amber-500/10 text-amber-400 border-amber-500/20'
  return 'bg-muted text-muted-foreground border-border/50'
}

function AccountsTab({ customer, role }: { customer: Customer; role: UserRole }) {
  const router = useRouter()
  const [isPending, startTransition] = useTransition()
  const [addOpen, setAddOpen] = useState(false)
  const [editAccount, setEditAccount] = useState<Account | null>(null)
  const { healthMap, healthLoading } = useSessionsHealth()
  const accounts = customer.accounts ?? []
  const expiredCount = accounts.filter((acct) => healthMap[acct.profile_name]?.status === 'expired').length

  const handleDelete = (account: Account) => {
    if (!window.confirm(`Delete account ${account.display_name}?`)) return
    startTransition(async () => {
      const res = await deleteAccount(customer.id, account.id)
      if (res?.error) {
        toast.error('Failed to delete account', { description: res.error })
        return
      }
      toast.success('Account deleted')
      router.refresh()
    })
  }

  if (accounts.length === 0) {
    return (
      <div className="space-y-3">
        {role === 'super_user' && (
          <Button size="sm" onClick={() => setAddOpen(true)}>
            <HugeiconsIcon icon={Add01Icon} strokeWidth={2} className="size-4 mr-1" />
            Add Account
          </Button>
        )}
        <p className="text-sm text-muted-foreground py-2">No accounts configured.</p>
        {role === 'super_user' && (
          <AccountSheet customerId={customer.id} open={addOpen} onClose={() => setAddOpen(false)} />
        )}
      </div>
    )
  }
  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="text-xs text-muted-foreground">
          {healthLoading ? 'Checking session status...' : `${expiredCount} expired session${expiredCount === 1 ? '' : 's'}`}
        </div>
        {role === 'super_user' && (
          <Button size="sm" onClick={() => setAddOpen(true)} disabled={isPending}>
            <HugeiconsIcon icon={Add01Icon} strokeWidth={2} className="size-4 mr-1" />
            Add Account
          </Button>
        )}
      </div>
      <Table>
        <TableHeader>
          <TableRow className="border-border/50">
            <TableHead className="text-xs">Display Name</TableHead>
            <TableHead className="text-xs">Profile</TableHead>
            <TableHead className="text-xs">Account ID</TableHead>
            <TableHead className="text-xs">Region</TableHead>
            <TableHead className="text-xs">Auth</TableHead>
            <TableHead className="text-xs">Status</TableHead>
            <TableHead className="text-xs">Session</TableHead>
            {role === 'super_user' && <TableHead className="text-xs text-right">Actions</TableHead>}
          </TableRow>
        </TableHeader>
        <TableBody>
          {accounts.map((acct) => {
            const sessionStatus = healthMap[acct.profile_name]?.status
            return (
              <TableRow key={acct.id} className="border-border/30 hover:bg-muted/20">
                <TableCell className="text-sm font-medium">{acct.display_name}</TableCell>
                <TableCell className="text-xs font-mono text-muted-foreground">{acct.profile_name}</TableCell>
                <TableCell className="text-xs font-mono text-muted-foreground">
                  {acct.account_id ?? '—'}
                </TableCell>
                <TableCell className="text-xs text-muted-foreground">
                  {acct.region ?? '—'}
                </TableCell>
                <TableCell>
                  <AuthModeBadge mode={acct.auth_method} />
                </TableCell>
                <TableCell>
                  <Badge
                    className={cn(
                      'text-[10px]',
                      acct.is_active
                        ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                        : 'bg-muted text-muted-foreground border-border/50',
                    )}
                  >
                    {acct.is_active ? 'Active' : 'Inactive'}
                  </Badge>
                </TableCell>
                <TableCell>
                  {sessionStatus ? (
                    <Badge className={cn('text-[10px]', sessionBadgeClass(sessionStatus))}>
                      {sessionStatus}
                    </Badge>
                  ) : (
                    <span className="text-xs text-muted-foreground">—</span>
                  )}
                </TableCell>
                {role === 'super_user' && (
                  <TableCell>
                    <div className="flex items-center justify-end gap-2">
                      <Button
                        type="button"
                        size="sm"
                        variant="outline"
                        className="h-7 px-2 text-xs"
                        onClick={() => setEditAccount(acct)}
                      >
                        Edit
                      </Button>
                      <Button
                        type="button"
                        size="sm"
                        variant="ghost"
                        className="h-7 px-2 text-xs text-destructive hover:text-destructive"
                        onClick={() => handleDelete(acct)}
                        disabled={isPending}
                      >
                        Delete
                      </Button>
                    </div>
                  </TableCell>
                )}
              </TableRow>
            )
          })}
        </TableBody>
      </Table>
      {role === 'super_user' && (
        <>
          <AccountSheet customerId={customer.id} open={addOpen} onClose={() => setAddOpen(false)} />
          <AccountSheet
            customerId={customer.id}
            account={editAccount ?? undefined}
            open={!!editAccount}
            onClose={() => setEditAccount(null)}
          />
        </>
      )}
    </div>
  )
}

function FindingsTab({
  findings,
  total,
  customerId,
}: {
  findings: Finding[]
  total: number
  customerId: string
}) {
  if (findings.length === 0) {
    return (
      <p className="text-sm text-muted-foreground py-4">No active findings.</p>
    )
  }
  return (
    <div className="space-y-3">
      <Table>
        <TableHeader>
          <TableRow className="border-border/50">
            <TableHead className="text-xs">Account</TableHead>
            <TableHead className="text-xs">Check</TableHead>
            <TableHead className="text-xs">Severity</TableHead>
            <TableHead className="text-xs">Title</TableHead>
            <TableHead className="text-xs">Detected</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {findings.map((f) => (
            <TableRow key={f.id} className="border-border/30 hover:bg-muted/20">
              <TableCell className="text-xs text-muted-foreground">
                {f.account.display_name}
              </TableCell>
              <TableCell className="text-xs font-mono text-muted-foreground">
                {f.check_name}
              </TableCell>
              <TableCell>
                <SeverityBadge severity={f.severity} />
              </TableCell>
              <TableCell className="text-xs max-w-[280px] truncate">{f.title}</TableCell>
              <TableCell className="text-xs text-muted-foreground whitespace-nowrap">
                {formatDateFull(f.created_at)}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
      {total > findings.length && (
        <div className="flex justify-end">
          <Button variant="ghost" size="sm" asChild>
            <Link href={`/findings?customer_id=${customerId}`}>
              View all {total} findings
              <HugeiconsIcon icon={ArrowRight01Icon} strokeWidth={2} className="size-3.5 ml-1" />
            </Link>
          </Button>
        </div>
      )}
    </div>
  )
}

function HistoryTab({
  runs,
  total,
  customerId,
}: {
  runs: CheckRunSummary[]
  total: number
  customerId: string
}) {
  if (runs.length === 0) {
    return (
      <p className="text-sm text-muted-foreground py-4">No check runs yet.</p>
    )
  }
  return (
    <div className="space-y-3">
      <Table>
        <TableHeader>
          <TableRow className="border-border/50">
            <TableHead className="text-xs">Check</TableHead>
            <TableHead className="text-xs">Mode</TableHead>
            <TableHead className="text-xs">Results</TableHead>
            <TableHead className="text-xs">Duration</TableHead>
            <TableHead className="text-xs">Run At</TableHead>
            <TableHead className="text-xs w-8" />
          </TableRow>
        </TableHeader>
        <TableBody>
          {runs.map((run) => {
            const { ok, warn, error } = run.results_summary
            return (
              <TableRow key={run.check_run_id} className="border-border/30 hover:bg-muted/20">
                <TableCell className="text-xs font-mono">{run.check_name || run.check_mode}</TableCell>
                <TableCell>
                  <Badge className="bg-muted/50 text-muted-foreground border-border/40 text-[10px]">
                    {run.check_mode}
                  </Badge>
                </TableCell>
                <TableCell className="text-xs">
                  <span className="text-emerald-400">{ok} OK</span>
                  {warn > 0 && <span className="text-amber-400 ml-1">{warn} WARN</span>}
                  {error > 0 && <span className="text-red-400 ml-1">{error} ERR</span>}
                </TableCell>
                <TableCell className="text-xs font-mono text-muted-foreground">
                  {run.execution_time_seconds.toFixed(1)}s
                </TableCell>
                <TableCell className="text-xs text-muted-foreground whitespace-nowrap">
                  {formatDateFull(run.created_at)}
                </TableCell>
                <TableCell>
                  <Button variant="ghost" size="icon" className="size-6" asChild>
                    <Link href={`/history?run=${run.check_run_id}`}>
                      <HugeiconsIcon icon={LinkSquare01Icon} strokeWidth={2} className="size-3.5" />
                    </Link>
                  </Button>
                </TableCell>
              </TableRow>
            )
          })}
        </TableBody>
      </Table>
      {total > runs.length && (
        <div className="flex justify-end">
          <Button variant="ghost" size="sm" asChild>
            <Link href={`/history?customer_id=${customerId}`}>
              View all {total} runs
              <HugeiconsIcon icon={ArrowRight01Icon} strokeWidth={2} className="size-3.5 ml-1" />
            </Link>
          </Button>
        </div>
      )}
    </div>
  )
}

// ── main component ─────────────────────────────────────────────────────────────

interface CustomerDetailViewProps {
  customer: Customer
  findings: Finding[]
  findingsTotal: number
  runs: CheckRunSummary[]
  runsTotal: number
  role: UserRole
  defaultTab?: string
}

export function CustomerDetailView({
  customer,
  findings,
  findingsTotal,
  runs,
  runsTotal,
  role,
  defaultTab = 'accounts',
}: CustomerDetailViewProps) {
  const activeAccounts = customer.accounts.filter((a) => a.is_active).length
  const totalAccounts = customer.accounts.length

  return (
    <div className="space-y-6">
      {/* Customer meta row */}
      <div className="flex flex-wrap gap-4 text-sm">
        <div className="flex items-center gap-2 text-muted-foreground">
          <HugeiconsIcon icon={UserAccountIcon} strokeWidth={2} className="size-4" />
          <span>
            <span className="text-foreground font-medium">{activeAccounts}</span>
            {' / '}
            {totalAccounts} accounts active
          </span>
        </div>
        <div className="flex items-center gap-2 text-muted-foreground">
          <HugeiconsIcon icon={CheckmarkBadge01Icon} strokeWidth={2} className="size-4" />
          <span>
            {customer.checks.length > 0
              ? customer.checks.join(', ')
              : 'No checks configured'}
          </span>
        </div>
        <div className="flex items-center gap-2 text-muted-foreground">
          <HugeiconsIcon icon={Alert01Icon} strokeWidth={2} className="size-4" />
          <span>
            <span className="text-foreground font-medium">{findingsTotal}</span> active findings
          </span>
        </div>
      </div>

      {/* Tabs */}
      <Tabs defaultValue={defaultTab}>
        <TabsList className="bg-muted/40">
          <TabsTrigger value="accounts" className="gap-1.5 text-xs">
            <HugeiconsIcon icon={UserAccountIcon} strokeWidth={2} className="size-3.5" />
            Accounts
            <Badge className="ml-1 bg-muted/60 text-muted-foreground border-border/40 text-[10px] px-1.5">
              {totalAccounts}
            </Badge>
          </TabsTrigger>
          <TabsTrigger value="findings" className="gap-1.5 text-xs">
            <HugeiconsIcon icon={Alert01Icon} strokeWidth={2} className="size-3.5" />
            Findings
            {findingsTotal > 0 && (
              <Badge className="ml-1 bg-red-500/10 text-red-400 border-red-500/20 text-[10px] px-1.5">
                {findingsTotal}
              </Badge>
            )}
          </TabsTrigger>
          <TabsTrigger value="history" className="gap-1.5 text-xs">
            <HugeiconsIcon icon={Clock01Icon} strokeWidth={2} className="size-3.5" />
            History
          </TabsTrigger>
        </TabsList>

        <TabsContent value="accounts" className="mt-4">
          <AccountsTab customer={customer} role={role} />
        </TabsContent>

        <TabsContent value="findings" className="mt-4">
          <FindingsTab findings={findings} total={findingsTotal} customerId={customer.id} />
        </TabsContent>

        <TabsContent value="history" className="mt-4">
          <HistoryTab runs={runs} total={runsTotal} customerId={customer.id} />
        </TabsContent>
      </Tabs>
    </div>
  )
}
