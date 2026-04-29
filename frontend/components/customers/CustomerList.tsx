'use client'

import { useState, useTransition, useMemo } from 'react'
import { useRouter } from 'next/navigation'
import { toast } from 'sonner'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { EmptyState } from '@/components/common/EmptyState'
import { ConfirmDialog } from '@/components/common/ConfirmDialog'
import { CustomerSheet } from '@/components/customers/CustomerSheet'
import { AccountSheet } from '@/components/customers/AccountSheet'
import { deleteCustomer, deleteAccount } from '@/app/(dashboard)/customers/actions'
import { HugeiconsIcon } from '@hugeicons/react'
import {
  UserAccountIcon,
  Add01Icon,
  MoreHorizontalIcon,
  PencilEdit01Icon,
  Delete01Icon,
  AlertCircleIcon,
  RefreshIcon,
  Search01Icon,
  UserAdd01Icon,
} from '@hugeicons/core-free-icons'
import { useSessionsHealth } from '@/components/customers/useSessionsHealth'
import type { Customer } from '@/lib/types/api'
import { cn } from '@/lib/utils'

// ── avatar helpers ────────────────────────────────────────────────────────────

const AVATAR_COLORS = [
  'bg-blue-500/15 text-blue-400 border-blue-500/20',
  'bg-violet-500/15 text-violet-400 border-violet-500/20',
  'bg-emerald-500/15 text-emerald-400 border-emerald-500/20',
  'bg-orange-500/15 text-orange-400 border-orange-500/20',
  'bg-pink-500/15 text-pink-400 border-pink-500/20',
  'bg-cyan-500/15 text-cyan-400 border-cyan-500/20',
  'bg-amber-500/15 text-amber-400 border-amber-500/20',
  'bg-rose-500/15 text-rose-400 border-rose-500/20',
  'bg-teal-500/15 text-teal-400 border-teal-500/20',
  'bg-indigo-500/15 text-indigo-400 border-indigo-500/20',
]

function avatarColor(name: string) {
  let h = 0
  for (const c of name) h = (h * 31 + c.charCodeAt(0)) & 0x7fffffff
  return AVATAR_COLORS[h % AVATAR_COLORS.length]
}

function initials(displayName: string) {
  return displayName
    .split(/\s+/)
    .slice(0, 2)
    .map((w) => w[0])
    .join('')
    .toUpperCase()
}

const CHECK_LABELS: Record<string, string> = {
  guardduty: 'GuardDuty',
  cloudwatch: 'CloudWatch',
  notifications: 'Notif',
  backup: 'Backup',
  cost: 'Cost',
  ec2_utilization: 'EC2 Util',
  'daily-arbel': 'Arbel',
  'daily-arbel-rds': 'Arbel RDS',
  'daily-arbel-ec2': 'Arbel EC2',
  ec2list: 'EC2 List',
  alarm_verification: 'Alarms',
  'daily-budget': 'Budget',
  'aws-utilization-3core': 'Utilization',
  health: 'Health',
}

interface CustomerListProps {
  customers: Customer[]
  role: string
}

export function CustomerList({ customers, role }: CustomerListProps) {
  const router = useRouter()
  const [search, setSearch] = useState('')
  const [createOpen, setCreateOpen] = useState(false)
  const [editTarget, setEditTarget] = useState<Customer | null>(null)
  const [deleteTarget, setDeleteTarget] = useState<Customer | null>(null)
  const [addAccountTarget, setAddAccountTarget] = useState<string | null>(null)
  const [isPending, startTransition] = useTransition()

  const { healthMap, healthLoading, healthError, lastCheckedAt, refresh: refreshHealth } =
    useSessionsHealth()

  // ── filtered list ─────────────────────────────────────────────────────────

  const filtered = useMemo(() => {
    if (!search.trim()) return customers
    const q = search.toLowerCase()
    return customers.filter(
      (c) =>
        c.display_name.toLowerCase().includes(q) ||
        c.name.toLowerCase().includes(q) ||
        (c.label ?? '').toLowerCase().includes(q),
    )
  }, [customers, search])

  // ── handlers ──────────────────────────────────────────────────────────────

  const handleDeleteCustomer = () => {
    if (!deleteTarget) return
    const name = deleteTarget.display_name
    startTransition(async () => {
      const res = await deleteCustomer(deleteTarget.id)
      if (res?.error) toast.error('Failed to delete customer', { description: res.error })
      else toast.success(`${name} deleted`)
      setDeleteTarget(null)
    })
  }

  // ── summary stats ─────────────────────────────────────────────────────────

  const totalAccounts = customers.reduce((s, c) => s + c.accounts.length, 0)
  const activeAccounts = customers.reduce(
    (s, c) => s + c.accounts.filter((a) => a.is_active).length,
    0,
  )
  const expiredTotal = Object.values(healthMap).filter((p) => p.status === 'expired').length
  const lastCheckLabel = lastCheckedAt
    ? new Date(lastCheckedAt).toLocaleTimeString('en-GB', {
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
      })
    : '--:--:--'

  // ── empty ─────────────────────────────────────────────────────────────────

  if (customers.length === 0) {
    return (
      <>
        <EmptyState
          icon={<HugeiconsIcon icon={UserAccountIcon} strokeWidth={1.5} className="size-10" />}
          title="No customers found"
          description="Add your first customer to get started."
          action={
            role === 'super_user' ? (
              <Button size="sm" onClick={() => setCreateOpen(true)}>
                <HugeiconsIcon icon={Add01Icon} strokeWidth={2} className="size-4 mr-1.5" />
                New Customer
              </Button>
            ) : undefined
          }
        />
        {role === 'super_user' && (
          <CustomerSheet open={createOpen} onClose={() => setCreateOpen(false)} />
        )}
      </>
    )
  }

  return (
    <div className="space-y-3">
      {/* ── Top bar ─────────────────────────────────────────────────────────── */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        {/* Stats */}
        <div className="flex flex-wrap items-center gap-2 sm:gap-4 text-sm text-muted-foreground">
          <span>
            <span className="font-semibold text-foreground tabular-nums">{customers.length}</span>{' '}
            customer{customers.length !== 1 ? 's' : ''}
          </span>
          <span className="text-border">|</span>
          <span>
            <span className="font-semibold text-foreground tabular-nums">{activeAccounts}</span>
            <span className="text-muted-foreground/60">/{totalAccounts}</span> accounts active
          </span>
          {!healthLoading && !healthError && expiredTotal > 0 && (
            <>
              <span className="text-border">|</span>
              <span className="flex items-center gap-1 text-xs text-red-400">
                <HugeiconsIcon icon={AlertCircleIcon} strokeWidth={2} className="size-3.5" />
                <span className="font-semibold tabular-nums">{expiredTotal}</span> session
                {expiredTotal !== 1 ? 's' : ''} expired
              </span>
            </>
          )}
          {!healthLoading && !healthError && expiredTotal === 0 && lastCheckedAt && (
            <>
              <span className="text-border">|</span>
              <span className="text-xs text-emerald-500/80">All sessions active</span>
            </>
          )}
          <span className="text-xs text-muted-foreground/60 tabular-nums">
            Last check {lastCheckLabel}
          </span>
        </div>

        {/* Actions */}
        <div className="flex items-center gap-2 shrink-0">
          <Button
            size="sm"
            variant="outline"
            onClick={refreshHealth}
            disabled={healthLoading}
            className="min-w-[138px] justify-center"
          >
            <HugeiconsIcon
              icon={RefreshIcon}
              strokeWidth={2}
              className={cn('size-4 mr-1.5', healthLoading && 'animate-spin')}
            />
            Refresh Session
          </Button>
          {role === 'super_user' && (
            <Button size="sm" onClick={() => setCreateOpen(true)}>
              <HugeiconsIcon icon={Add01Icon} strokeWidth={2} className="size-4 mr-1.5" />
              New Customer
            </Button>
          )}
        </div>
      </div>

      {/* ── Search ──────────────────────────────────────────────────────────── */}
      <div className="relative max-w-sm">
        <HugeiconsIcon
          icon={Search01Icon}
          strokeWidth={2}
          className="absolute left-2.5 top-1/2 -translate-y-1/2 size-4 text-muted-foreground pointer-events-none"
        />
        <Input
          placeholder="Search customers…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="pl-8 h-8 text-sm"
        />
      </div>

      {/* ── Table ───────────────────────────────────────────────────────────── */}
      <div className="rounded-lg border border-border/60 overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow className="bg-muted/30 hover:bg-muted/30">
              <TableHead className="w-[220px] text-xs uppercase tracking-wider">Customer</TableHead>
              <TableHead className="text-xs uppercase tracking-wider text-center w-[100px]">Accounts</TableHead>
              <TableHead className="text-xs uppercase tracking-wider">Checks</TableHead>
              <TableHead className="text-xs uppercase tracking-wider w-[90px]">Mode</TableHead>
              <TableHead className="text-xs uppercase tracking-wider w-[110px]">Session</TableHead>
              {role === 'super_user' && (
                <TableHead className="w-10" />
              )}
            </TableRow>
          </TableHeader>
          <TableBody>
            {filtered.length === 0 && (
              <TableRow>
                <TableCell colSpan={role === 'super_user' ? 6 : 5} className="text-center text-sm text-muted-foreground py-8">
                  No customers match &ldquo;{search}&rdquo;
                </TableCell>
              </TableRow>
            )}
            {filtered.map((customer) => {
              const active = customer.accounts.filter((a) => a.is_active).length
              const total = customer.accounts.length
              const maxChips = 3

              // Session health for this customer's accounts
              const expiredCount = customer.accounts.filter(
                (a) => healthMap[a.profile_name]?.status === 'expired',
              ).length

              return (
                <TableRow
                  key={customer.id}
                  className="cursor-pointer hover:bg-muted/30 transition-colors"
                  onClick={() => router.push(`/customers/${customer.id}`)}
                >
                  {/* Customer name */}
                  <TableCell className="py-3">
                    <div className="flex items-center gap-2.5 min-w-0">
                      <Avatar
                        className={cn(
                          'size-7 rounded-md border text-[11px] font-bold shrink-0',
                          avatarColor(customer.name),
                        )}
                      >
                        <AvatarFallback
                          className={cn(
                            'rounded-md text-[11px] font-bold',
                            avatarColor(customer.name),
                          )}
                        >
                          {initials(customer.display_name)}
                        </AvatarFallback>
                      </Avatar>
                      <div className="min-w-0">
                        <div className="flex items-center gap-1.5 flex-wrap">
                          <span className="text-sm font-medium text-foreground truncate">
                            {customer.display_name}
                          </span>
                          {customer.label && (
                            <Badge variant="outline" className="h-4 px-1.5 text-[10px] shrink-0">
                              {customer.label}
                            </Badge>
                          )}
                        </div>
                        <span className="text-[10px] text-muted-foreground font-mono">
                          {customer.name}
                        </span>
                      </div>
                    </div>
                  </TableCell>

                  {/* Accounts */}
                  <TableCell className="text-center tabular-nums text-sm">
                    <span className="text-foreground font-medium">{active}</span>
                    <span className="text-muted-foreground/60 text-xs">/{total}</span>
                  </TableCell>

                  {/* Checks */}
                  <TableCell>
                    <div className="flex items-center gap-1 flex-wrap">
                      {customer.checks.slice(0, maxChips).map((c) => (
                        <span
                          key={c}
                          className="text-[10px] bg-muted text-muted-foreground border border-border/50 px-1.5 py-px rounded font-mono"
                        >
                          {CHECK_LABELS[c] ?? c}
                        </span>
                      ))}
                      {customer.checks.length > maxChips && (
                        <span className="text-[10px] text-muted-foreground/70">
                          +{customer.checks.length - maxChips}
                        </span>
                      )}
                      {customer.checks.length === 0 && (
                        <span className="text-[10px] text-muted-foreground/40">—</span>
                      )}
                    </div>
                  </TableCell>

                  {/* Report mode */}
                  <TableCell>
                    <Badge
                      variant="outline"
                      className={cn(
                        'text-[10px] h-5 px-1.5',
                        customer.report_mode === 'detailed'
                          ? 'bg-blue-500/10 text-blue-400 border-blue-500/20'
                          : customer.report_mode === 'simple'
                          ? 'bg-amber-500/10 text-amber-400 border-amber-500/20'
                          : 'bg-muted text-muted-foreground border-border/50',
                      )}
                    >
                      {customer.report_mode === 'detailed'
                        ? 'Detailed'
                        : customer.report_mode === 'simple'
                        ? 'Simple'
                        : 'Summary'}
                    </Badge>
                  </TableCell>

                  {/* Session health */}
                  <TableCell>
                    {healthLoading ? (
                      <Skeleton className="h-4 w-16 rounded" />
                    ) : expiredCount > 0 ? (
                      <span className="flex items-center gap-1 text-[10px] text-red-400">
                        <HugeiconsIcon icon={AlertCircleIcon} strokeWidth={2} className="size-3.5" />
                        {expiredCount} expired
                      </span>
                    ) : lastCheckedAt ? (
                      <span className="text-[10px] text-emerald-500/80">OK</span>
                    ) : (
                      <span className="text-[10px] text-muted-foreground/40">—</span>
                    )}
                  </TableCell>

                  {/* Actions */}
                  {role === 'super_user' && (
                    <TableCell onClick={(e) => e.stopPropagation()}>
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-7 w-7 text-muted-foreground hover:text-foreground"
                          >
                            <HugeiconsIcon icon={MoreHorizontalIcon} strokeWidth={2} className="size-4" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end" className="w-44">
                          <DropdownMenuItem onClick={() => setEditTarget(customer)}>
                            <HugeiconsIcon icon={PencilEdit01Icon} strokeWidth={2} className="size-4 mr-2" />
                            Edit customer
                          </DropdownMenuItem>
                          <DropdownMenuItem onClick={() => setAddAccountTarget(customer.id)}>
                            <HugeiconsIcon icon={UserAdd01Icon} strokeWidth={2} className="size-4 mr-2" />
                            Add account
                          </DropdownMenuItem>
                          <DropdownMenuSeparator />
                          <DropdownMenuItem
                            className="text-destructive focus:text-destructive"
                            onClick={() => setDeleteTarget(customer)}
                          >
                            <HugeiconsIcon icon={Delete01Icon} strokeWidth={2} className="size-4 mr-2" />
                            Delete customer
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </TableCell>
                  )}
                </TableRow>
              )
            })}
          </TableBody>
        </Table>
      </div>

      {/* ── Sheets & dialogs ─────────────────────────────────────────────────── */}
      {role === 'super_user' && (
        <>
          <CustomerSheet open={createOpen} onClose={() => setCreateOpen(false)} />
          <CustomerSheet
            customer={editTarget ?? undefined}
            open={!!editTarget}
            onClose={() => setEditTarget(null)}
          />
          <AccountSheet
            customerId={addAccountTarget ?? ''}
            open={!!addAccountTarget}
            onClose={() => setAddAccountTarget(null)}
          />
          <ConfirmDialog
            open={!!deleteTarget}
            onOpenChange={(v) => !v && setDeleteTarget(null)}
            title={`Delete ${deleteTarget?.display_name ?? 'customer'}?`}
            description="This will permanently delete the customer and all associated accounts and data."
            confirmLabel="Delete"
            destructive
            isPending={isPending}
            onConfirm={handleDeleteCustomer}
          />
        </>
      )}
    </div>
  )
}
