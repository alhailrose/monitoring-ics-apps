'use client'

import { useState, useTransition, useEffect } from 'react'
import { toast } from 'sonner'
import { Card, CardContent, CardHeader } from '@/components/ui/card'
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Skeleton } from '@/components/ui/skeleton'
import { EmptyState } from '@/components/common/EmptyState'
import { ConfirmDialog } from '@/components/common/ConfirmDialog'
import { CustomerSheet } from '@/components/customers/CustomerSheet'
import { AccountSheet } from '@/components/customers/AccountSheet'
import { AccountDetailsSheet } from '@/components/customers/AccountDetailsSheet'
import { AccountRow } from '@/components/customers/AccountRow'
import { deleteCustomer, deleteAccount } from '@/app/(dashboard)/customers/actions'
import { HugeiconsIcon } from '@hugeicons/react'
import {
  ArrowDown01Icon,
  UserAdd01Icon,
  UserAccountIcon,
  Add01Icon,
  MoreHorizontalIcon,
  PencilEdit01Icon,
  Delete01Icon,
  AlertCircleIcon,
} from '@hugeicons/core-free-icons'
import type { Customer, Account, SessionsHealth, ProfileHealth } from '@/lib/types/api'
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

// ── check label map ───────────────────────────────────────────────────────────

const CHECK_LABELS: Record<string, string> = {
  guardduty: 'GuardDuty',
  cloudwatch: 'CloudWatch',
  notifications: 'Notifications',
  backup: 'Backup',
  cost: 'Cost',
  'ec2_utilization':  'EC2 Util',
  'daily-arbel':      'Arbel',
  'daily-arbel-rds':  'Arbel RDS',
  'daily-arbel-ec2':  'Arbel EC2',
  ec2list:            'EC2 List',
  alarm_verification: 'Alarms',
  'daily-budget':     'Budget',
  'aws-utilization-3core': 'Utilization',
  health: 'Health',
}

// ── props ─────────────────────────────────────────────────────────────────────

interface CustomerListProps {
  customers: Customer[]
  role: string
}

// ── component ─────────────────────────────────────────────────────────────────

export function CustomerList({ customers, role }: CustomerListProps) {
  const [createOpen, setCreateOpen] = useState(false)
  const [editTarget, setEditTarget] = useState<Customer | null>(null)
  const [deleteTarget, setDeleteTarget] = useState<Customer | null>(null)
  const [addAccountTarget, setAddAccountTarget] = useState<string | null>(null)
  const [editAccountTarget, setEditAccountTarget] = useState<{
    customerId: string
    account: Account
  } | null>(null)
  const [deleteAccountTarget, setDeleteAccountTarget] = useState<{
    customerId: string
    accountId: string
  } | null>(null)
  const [detailsAccountTarget, setDetailsAccountTarget] = useState<Account | null>(null)
  const [isPending, startTransition] = useTransition()
  const [sessionsHealth, setSessionsHealth] = useState<SessionsHealth | null>(null)
  const [healthLoading, setHealthLoading] = useState(true)
  const [healthError, setHealthError] = useState(false)

  useEffect(() => {
    fetch('/api/sessions-health')
      .then((r) => {
        if (!r.ok) throw new Error('health check failed')
        return r.json()
      })
      .then((data) => {
        setSessionsHealth(data)
        setHealthLoading(false)
      })
      .catch(() => {
        setHealthError(true)
        setHealthLoading(false)
      })
  }, [])

  const healthMap: Record<string, ProfileHealth> = {}
  if (sessionsHealth?.profiles) {
    for (const p of sessionsHealth.profiles) healthMap[p.profile_name] = p
  }

  const handleDeleteCustomer = () => {
    if (!deleteTarget) return
    const name = deleteTarget.display_name
    startTransition(async () => {
      const res = await deleteCustomer(deleteTarget.id)
      if (res?.error) {
        toast.error('Failed to delete customer', { description: res.error })
      } else {
        toast.success(`${name} deleted`)
      }
      setDeleteTarget(null)
    })
  }

  const handleDeleteAccount = () => {
    if (!deleteAccountTarget) return
    startTransition(async () => {
      const res = await deleteAccount(
        deleteAccountTarget.customerId,
        deleteAccountTarget.accountId,
      )
      if (res?.error) {
        toast.error('Failed to delete account', { description: res.error })
      } else {
        toast.success('Account deleted')
      }
      setDeleteAccountTarget(null)
    })
  }

  // ── summary stats ─────────────────────────────────────────────────────────

  const totalAccounts = customers.reduce((s, c) => s + c.accounts.length, 0)
  const activeAccounts = customers.reduce(
    (s, c) => s + c.accounts.filter((a) => a.is_active).length,
    0,
  )
  const expiredSessions = sessionsHealth?.expired ?? 0

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
      {/* ── Stats bar ───────────────────────────────────────────────────────── */}
      <div className="flex items-center justify-between gap-4">
        <div className="flex items-center gap-4 text-sm text-muted-foreground">
          <span>
            <span className="font-semibold text-foreground tabular-nums">
              {customers.length}
            </span>{' '}
            customer{customers.length !== 1 ? 's' : ''}
          </span>
          <span className="text-border">|</span>
          <span>
            <span className="font-semibold text-foreground tabular-nums">{activeAccounts}</span>
            <span className="text-muted-foreground/60">/{totalAccounts}</span> accounts active
          </span>
          {healthLoading && (
            <>
              <span className="text-border">|</span>
              <Skeleton className="h-4 w-28 rounded" />
            </>
          )}
          {!healthLoading && healthError && (
            <>
              <span className="text-border">|</span>
              <span className="flex items-center gap-1 text-amber-400/80 text-xs">
                <HugeiconsIcon icon={AlertCircleIcon} strokeWidth={2} className="size-3.5" />
                Session status unavailable
              </span>
            </>
          )}
          {!healthLoading && !healthError && expiredSessions > 0 && (
            <>
              <span className="text-border">|</span>
              <span className="flex items-center gap-1 text-red-400">
                <HugeiconsIcon icon={AlertCircleIcon} strokeWidth={2} className="size-3.5" />
                <span className="font-semibold tabular-nums">{expiredSessions}</span> session
                {expiredSessions !== 1 ? 's' : ''} expired
              </span>
            </>
          )}
        </div>

        {role === 'super_user' && (
          <Button size="sm" onClick={() => setCreateOpen(true)}>
            <HugeiconsIcon icon={Add01Icon} strokeWidth={2} className="size-4 mr-1.5" />
            New Customer
          </Button>
        )}
      </div>

      {/* ── Customer cards ──────────────────────────────────────────────────── */}
      {customers.map((customer) => {
        const active = customer.accounts.filter((a) => a.is_active).length
        const total = customer.accounts.length
        const maxCheckChips = 4

        // Session health summary for this customer
        const customerExpired = customer.accounts.filter(
          (a) => healthMap[a.profile_name]?.status === 'expired',
        ).length
        const customerUnknown = !healthLoading && !healthError && customer.accounts.some(
          (a) => a.auth_method === 'profile' && !healthMap[a.profile_name],
        )

        return (
          <Collapsible key={customer.id} defaultOpen={false}>
            <Card className="border-border/60 overflow-hidden transition-shadow hover:shadow-sm">
              <CardHeader className="p-0">
                <div className="flex items-center px-3 py-2">
                  <CollapsibleTrigger asChild>
                    <button className="flex items-center gap-2.5 flex-1 min-w-0 text-left group">
                      {/* Avatar */}
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

                      {/* Info */}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-1.5 flex-wrap">
                          <span className="text-sm font-medium text-foreground">
                            {customer.display_name}
                          </span>
                          <span className="text-[10px] text-muted-foreground font-mono bg-muted/60 px-1.5 py-0.5 rounded">
                            {customer.name}
                          </span>
                          {customer.label && (
                            <Badge variant="outline" className="h-4 px-1.5 text-[10px]">
                              {customer.label}
                            </Badge>
                          )}
                          <Badge className={cn(
                            'h-4 px-1.5 text-[10px]',
                            customer.report_mode === 'detailed'
                              ? 'bg-blue-500/10 text-blue-400 border-blue-500/20'
                              : 'bg-muted text-muted-foreground border-border/50',
                          )}>
                            {customer.report_mode === 'detailed' ? 'Detailed' : 'Summary'}
                          </Badge>
                          {customer.slack_enabled && (
                            <Badge className="h-4 px-1.5 text-[10px] bg-green-500/10 text-green-400 border-green-500/20">
                              Slack
                            </Badge>
                          )}
                        </div>
                        <div className="flex items-center gap-2 mt-0.5 flex-wrap">
                          <span className="text-xs text-muted-foreground">
                            <span className="text-foreground font-medium">{active}</span>
                            <span className="text-muted-foreground/60">/{total}</span> accounts
                          </span>
                          {healthLoading && (
                            <Skeleton className="h-3.5 w-14 rounded-full" />
                          )}
                          {!healthLoading && customerExpired > 0 && (
                            <span className="flex items-center gap-1 text-[10px] text-red-400 bg-red-500/10 border border-red-500/20 rounded-full px-1.5 py-px">
                              <HugeiconsIcon icon={AlertCircleIcon} strokeWidth={2} className="size-3" />
                              {customerExpired} session{customerExpired !== 1 ? 's' : ''} expired
                            </span>
                          )}
                          {!healthLoading && customerExpired === 0 && customerUnknown && (
                            <span className="text-[10px] text-muted-foreground/50">
                              session status unknown
                            </span>
                          )}
                          {customer.checks.length > 0 && (
                            <span className="flex items-center gap-1 flex-wrap">
                              {customer.checks.slice(0, maxCheckChips).map((c) => (
                                <span
                                  key={c}
                                  className="text-[10px] bg-muted text-muted-foreground border border-border/50 px-1.5 py-px rounded font-mono"
                                >
                                  {CHECK_LABELS[c] ?? c}
                                </span>
                              ))}
                              {customer.checks.length > maxCheckChips && (
                                <span className="text-[10px] text-muted-foreground">
                                  +{customer.checks.length - maxCheckChips}
                                </span>
                              )}
                            </span>
                          )}
                        </div>
                      </div>

                      <HugeiconsIcon
                        icon={ArrowDown01Icon}
                        strokeWidth={2}
                        className="size-4 shrink-0 text-muted-foreground/60 transition-transform group-data-[state=open]:rotate-180 mr-1"
                      />
                    </button>
                  </CollapsibleTrigger>

                  {/* Actions dropdown */}
                  {role === 'super_user' && (
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-7 w-7 text-muted-foreground hover:text-foreground shrink-0"
                          onClick={(e) => e.stopPropagation()}
                        >
                          <HugeiconsIcon
                            icon={MoreHorizontalIcon}
                            strokeWidth={2}
                            className="size-4"
                          />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end" className="w-44">
                        <DropdownMenuItem onClick={() => setEditTarget(customer)}>
                          <HugeiconsIcon
                            icon={PencilEdit01Icon}
                            strokeWidth={2}
                            className="size-4 mr-2"
                          />
                          Edit customer
                        </DropdownMenuItem>
                        <DropdownMenuItem onClick={() => setAddAccountTarget(customer.id)}>
                          <HugeiconsIcon
                            icon={UserAdd01Icon}
                            strokeWidth={2}
                            className="size-4 mr-2"
                          />
                          Add account
                        </DropdownMenuItem>
                        <DropdownMenuSeparator />
                        <DropdownMenuItem
                          className="text-destructive focus:text-destructive"
                          onClick={() => setDeleteTarget(customer)}
                        >
                          <HugeiconsIcon
                            icon={Delete01Icon}
                            strokeWidth={2}
                            className="size-4 mr-2"
                          />
                          Delete customer
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  )}
                </div>
              </CardHeader>

              <CollapsibleContent>
                <CardContent className="px-0 pb-0 pt-0">
                  {customer.accounts.length === 0 ? (
                    <p className="px-3 py-3 text-xs text-muted-foreground border-t border-border/40">
                      No accounts configured.
                    </p>
                  ) : (
                    <>
                      <div className="grid grid-cols-[1fr_auto] sm:grid-cols-[1fr_120px_100px_auto] gap-x-3 px-3 py-1.5 text-[11px] font-medium text-muted-foreground uppercase tracking-wider border-t border-border/40 bg-muted/20">
                        <span>Account</span>
                        <span className="hidden sm:block text-center">Auth</span>
                        <span className="hidden sm:block text-center">Session</span>
                        {role === 'super_user' ? <span className="w-8" /> : null}
                      </div>
                      {customer.accounts.map((acc) => (
                        <AccountRow
                          key={acc.id}
                          account={acc}
                          healthMap={healthMap}
                          healthLoading={healthLoading}
                          role={role}
                          onEdit={(a) =>
                            setEditAccountTarget({ customerId: customer.id, account: a })
                          }
                          onDelete={(id) =>
                            setDeleteAccountTarget({ customerId: customer.id, accountId: id })
                          }
                          onDetails={(a) => setDetailsAccountTarget(a)}
                        />
                      ))}
                    </>
                  )}

                  {role === 'super_user' && customer.accounts.length > 0 && (
                    <div className="px-3 py-2 border-t border-border/30 bg-muted/10">
                      <button
                        className="flex items-center gap-1.5 text-xs text-muted-foreground hover:text-foreground transition-colors"
                        onClick={() => setAddAccountTarget(customer.id)}
                      >
                        <HugeiconsIcon icon={UserAdd01Icon} strokeWidth={2} className="size-3.5" />
                        Add account
                      </button>
                    </div>
                  )}
                </CardContent>
              </CollapsibleContent>
            </Card>
          </Collapsible>
        )
      })}

      {/* ── Sheets & dialogs ─────────────────────────────────────────────────── */}
      <AccountDetailsSheet
        account={detailsAccountTarget}
        open={!!detailsAccountTarget}
        onClose={() => setDetailsAccountTarget(null)}
      />

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
          <AccountSheet
            key={editAccountTarget?.account?.id ?? 'edit-account'}
            customerId={editAccountTarget?.customerId ?? ''}
            account={editAccountTarget?.account}
            open={!!editAccountTarget}
            onClose={() => setEditAccountTarget(null)}
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
          <ConfirmDialog
            open={!!deleteAccountTarget}
            onOpenChange={(v) => !v && setDeleteAccountTarget(null)}
            title="Delete account?"
            description="This will permanently remove the account from this customer."
            confirmLabel="Delete"
            destructive
            isPending={isPending}
            onConfirm={handleDeleteAccount}
          />
        </>
      )}
    </div>
  )
}
