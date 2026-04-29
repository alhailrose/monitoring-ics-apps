'use client'

import { useMemo, useState } from 'react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog'
import type { Customer, SessionsHealth } from '@/lib/types/api'

type CustomerSessionState = 'active' | 'expired' | 'error' | 'no_config' | 'non_sso'

interface CustomerSessionRow {
  customerId: string
  customerName: string
  state: CustomerSessionState
  activeProfiles: number
  totalProfiles: number
}

interface SessionStatusPopupProps {
  customers: Customer[]
}

function stateLabel(state: CustomerSessionState): string {
  if (state === 'active') return 'Active'
  if (state === 'expired') return 'Expired'
  if (state === 'error') return 'Error'
  if (state === 'non_sso') return 'N/A (Non-SSO)'
  return 'No Config'
}

function stateBadgeClass(state: CustomerSessionState): string {
  if (state === 'active') return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
  if (state === 'expired') return 'bg-amber-500/10 text-amber-300 border-amber-500/20'
  if (state === 'error') return 'bg-red-500/10 text-red-400 border-red-500/20'
  if (state === 'non_sso') return 'bg-blue-500/10 text-blue-300 border-blue-500/20'
  return 'bg-muted text-muted-foreground border-border/50'
}

function aggregateByCustomer(customers: Customer[], report: SessionsHealth): CustomerSessionRow[] {
  const profileMap: Record<string, string> = {}
  for (const profile of report.profiles ?? []) {
    profileMap[profile.profile_name] = profile.status
  }

  return customers
    .map((customer) => {
      const profiles = [
        ...new Set(
          customer.accounts
            .filter((a) => (a.auth_method ?? 'profile') === 'profile')
            .map((a) => a.profile_name)
            .filter(Boolean),
        ),
      ]
      const nonSsoAccounts = customer.accounts.filter(
        (a) => (a.auth_method ?? 'profile') !== 'profile',
      ).length

      if (profiles.length === 0 && nonSsoAccounts > 0) {
        return {
          customerId: customer.id,
          customerName: customer.display_name,
          state: 'non_sso' as const,
          activeProfiles: nonSsoAccounts,
          totalProfiles: nonSsoAccounts,
        }
      }

      if (profiles.length === 0) {
        return {
          customerId: customer.id,
          customerName: customer.display_name,
          state: 'no_config' as const,
          activeProfiles: 0,
          totalProfiles: 0,
        }
      }

      const statuses = profiles.map((p) => profileMap[p] ?? 'missing')
      const activeProfiles = statuses.filter((s) => s === 'ok').length
      const hasError = statuses.includes('error')
      const hasExpired = statuses.includes('expired')
      const hasNoConfig = statuses.includes('no_config') || statuses.includes('missing')

      let state: CustomerSessionState = 'active'
      if (hasError) state = 'error'
      else if (hasExpired) state = 'expired'
      else if (hasNoConfig) state = 'no_config'

      return {
        customerId: customer.id,
        customerName: customer.display_name,
        state,
        activeProfiles,
        totalProfiles: profiles.length,
      }
    })
    .sort((a, b) => a.customerName.localeCompare(b.customerName))
}

export function SessionStatusPopup({ customers }: SessionStatusPopupProps) {
  const [open, setOpen] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [rows, setRows] = useState<CustomerSessionRow[] | null>(null)
  const [lastCheckedAt, setLastCheckedAt] = useState<Date | null>(null)

  const load = async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch('/api/sessions-health', { cache: 'no-store' })
      if (!res.ok) throw new Error('failed')
      const data = (await res.json()) as SessionsHealth
      setRows(aggregateByCustomer(customers, data))
      setLastCheckedAt(new Date())
    } catch {
      setRows(null)
      setError('Failed to load session status')
    } finally {
      setLoading(false)
    }
  }

  const onOpenChange = (nextOpen: boolean) => {
    setOpen(nextOpen)
    if (nextOpen && !rows && !loading) {
      void load()
    }
  }

  const body = useMemo(() => {
    if (loading) {
      return <p className="text-xs text-muted-foreground">Loading session status...</p>
    }
    if (error) {
      return (
        <div className="space-y-2">
          <p className="text-xs text-amber-300">{error}</p>
          <Button type="button" variant="outline" size="sm" onClick={() => void load()}>
            Retry
          </Button>
        </div>
      )
    }
    if (!rows || rows.length === 0) {
      return <p className="text-xs text-muted-foreground">No customers available.</p>
    }

    return (
      <div className="space-y-2 max-h-[50vh] overflow-y-auto pr-1">
        {rows.map((row) => (
          <div key={row.customerId} className="flex items-center justify-between rounded-md border border-border/50 bg-muted/20 px-2.5 py-2">
            <div className="min-w-0">
              <p className="text-xs font-medium truncate">{row.customerName}</p>
              <p className="text-[11px] text-muted-foreground">
                {row.state === 'non_sso'
                  ? `${row.totalProfiles} non-SSO account${row.totalProfiles === 1 ? '' : 's'}`
                  : `${row.activeProfiles}/${row.totalProfiles} active`}
              </p>
            </div>
            <Badge className={stateBadgeClass(row.state)}>{stateLabel(row.state)}</Badge>
          </div>
        ))}
      </div>
    )
  }, [error, loading, rows])

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogTrigger asChild>
        <Button type="button" variant="outline" size="sm">
          Session Status
        </Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-md" showCloseButton>
        <DialogHeader>
          <DialogTitle>Session Status</DialogTitle>
          <DialogDescription>
            Quick check session readiness by customer.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-3">
          <p className="text-[11px] text-muted-foreground">
            No Config applies to SSO/profile auth only. Access Key and Assume Role are marked as Non-SSO.
          </p>
          {lastCheckedAt && (
            <p className="text-[11px] text-muted-foreground">
              Last checked: {lastCheckedAt.toLocaleString()}
            </p>
          )}
          <div className="flex items-center justify-end">
            <Button type="button" variant="ghost" size="sm" onClick={() => void load()} disabled={loading}>
              Refresh
            </Button>
          </div>
          {body}
        </div>
      </DialogContent>
    </Dialog>
  )
}
