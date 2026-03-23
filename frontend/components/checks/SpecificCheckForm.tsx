'use client'

import { useState, useMemo, useTransition } from 'react'
import { toast } from 'sonner'
import { runChecks } from '@/app/(dashboard)/checks/actions'
import { ResultsTable } from '@/components/checks/ResultsTable'
import { CheckProgress } from '@/components/checks/CheckProgress'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { HugeiconsIcon } from '@hugeicons/react'
import {
  Shield01Icon,
  Chart01Icon,
  Notification01Icon,
  ArchiveRestoreIcon,
  DollarCircleIcon,
  Database01Icon,
  ComputerIcon,
  Alert01Icon,
} from '@hugeicons/core-free-icons'
import Link from 'next/link'
import { cn } from '@/lib/utils'
import type { Customer, ExecuteResponse } from '@/lib/types/api'

const CHECK_CARDS = [
  { value: 'guardduty',          label: 'GuardDuty',          icon: Shield01Icon,       color: 'text-blue-400' },
  { value: 'cloudwatch',         label: 'CloudWatch',          icon: Chart01Icon,        color: 'text-cyan-400' },
  { value: 'notifications',      label: 'Notifications',       icon: Notification01Icon, color: 'text-violet-400' },
  { value: 'backup',             label: 'Backup',              icon: ArchiveRestoreIcon, color: 'text-emerald-400' },
  { value: 'cost',               label: 'Cost',                icon: DollarCircleIcon,   color: 'text-amber-400' },
  { value: 'daily-arbel-rds',    label: 'RDS Utilization',     icon: Database01Icon,     color: 'text-orange-400' },
  { value: 'daily-arbel-ec2',    label: 'EC2 Utilization',     icon: ComputerIcon,       color: 'text-sky-400' },
  { value: 'alarm_verification', label: 'Alarm Verification',  icon: Alert01Icon,        color: 'text-red-400' },
  { value: 'daily-budget',       label: 'Daily Budget',        icon: DollarCircleIcon,   color: 'text-green-400' },
]

// Checks that support time window selection
const UTILIZATION_CHECKS = new Set(['daily-arbel-rds', 'daily-arbel-ec2'])

const TIME_WINDOWS = [
  { value: 1,  label: '1h' },
  { value: 3,  label: '3h' },
  { value: 12, label: '12h' },
]

interface SpecificCheckFormProps {
  customers: Customer[]
}

export function SpecificCheckForm({ customers }: SpecificCheckFormProps) {
  const [selectedAccountIds, setSelectedAccountIds] = useState<string[]>([])
  const [selectedCheckName, setSelectedCheckName] = useState(CHECK_CARDS[0].value)
  const [windowHours, setWindowHours] = useState(12)
  const [alarmSearch, setAlarmSearch] = useState('')
  const [accountSearch, setAccountSearch] = useState('')
  const [expandedCustomers, setExpandedCustomers] = useState<Set<string>>(new Set())
  const [results, setResults] = useState<ExecuteResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [isPending, startTransition] = useTransition()

  const showTimeWindow = UTILIZATION_CHECKS.has(selectedCheckName)

  const toggleAccount = (id: string) => {
    setSelectedAccountIds((prev) =>
      prev.includes(id) ? prev.filter((a) => a !== id) : [...prev, id],
    )
  }

  const toggleAllInCustomer = (customerAccIds: string[]) => {
    const allSelected = customerAccIds.every((id) => selectedAccountIds.includes(id))
    if (allSelected) {
      setSelectedAccountIds((prev) => prev.filter((id) => !customerAccIds.includes(id)))
    } else {
      setSelectedAccountIds((prev) => [...new Set([...prev, ...customerAccIds])])
    }
  }

  const toggleExpanded = (customerId: string) => {
    setExpandedCustomers((prev) => {
      const next = new Set(prev)
      if (next.has(customerId)) next.delete(customerId)
      else next.add(customerId)
      return next
    })
  }

  const allAccounts = customers.flatMap((c) => c.accounts)

  // Filter customers/accounts by search
  const filteredCustomers = useMemo(() => {
    if (!accountSearch.trim()) return customers
    const q = accountSearch.toLowerCase()
    return customers
      .map((c) => ({
        ...c,
        accounts: c.accounts.filter(
          (a) =>
            a.display_name.toLowerCase().includes(q) ||
            (a.account_id ?? '').includes(q) ||
            c.display_name.toLowerCase().includes(q),
        ),
      }))
      .filter((c) => c.accounts.length > 0)
  }, [customers, accountSearch])

  // Auto-expand customers that match search
  const visibleCustomers = useMemo(() => {
    if (accountSearch.trim()) return filteredCustomers // show all when searching
    return filteredCustomers
  }, [filteredCustomers, accountSearch])

  const isExpanded = (customerId: string) => {
    // When searching, always expand matching customers
    if (accountSearch.trim()) return true
    // When accounts are selected in a customer, expand it
    const customer = customers.find((c) => c.id === customerId)
    if (customer && customer.accounts.some((a) => selectedAccountIds.includes(a.id))) return true
    return expandedCustomers.has(customerId)
  }

  // Alarm names from selected accounts only — for alarm_verification
  const targetAccounts = selectedAccountIds.length > 0
    ? allAccounts.filter((a) => selectedAccountIds.includes(a.id))
    : []
  const alarmNames = targetAccounts
    .flatMap((a) => a.alarm_names ?? [])
    .filter((v, i, arr) => arr.indexOf(v) === i)
    .sort()
  const filteredAlarmNames = alarmSearch.trim()
    ? alarmNames.filter((n) => n.toLowerCase().includes(alarmSearch.toLowerCase()))
    : alarmNames

  // Derive customer_ids from selected accounts (or all customers if none selected)
  const derivedCustomerIds = selectedAccountIds.length > 0
    ? customers
        .filter((c) => c.accounts.some((a) => selectedAccountIds.includes(a.id)))
        .map((c) => c.id)
    : customers.map((c) => c.id)

  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    const formData = new FormData()
    formData.set('mode', 'single')
    formData.set('send_slack', 'false')
    formData.set('check_name', selectedCheckName)
    derivedCustomerIds.forEach((id) => formData.append('customer_ids', id))
    selectedAccountIds.forEach((id) => formData.append('account_ids', id))

    // Pass check_params (e.g. window_hours)
    if (showTimeWindow) {
      formData.set('check_params', JSON.stringify({ window_hours: windowHours }))
    }

    setError(null)
    setResults(null)
    startTransition(async () => {
      const res = await runChecks(formData)
      if (res.error) {
        setError(res.error)
        toast.error('Check failed', { description: res.error })
      } else if (res.data) {
        setResults(res.data)
        const total = res.data.results.length
        const ok = res.data.results.filter((r) => r.status === 'OK').length
        toast.success('Checks completed', { description: `${ok}/${total} passed` })
      }
    })
  }

  const hasCustomers = customers.length > 0
  const isAlarmCheck = selectedCheckName === 'alarm_verification'

  return (
    <div className="space-y-6">
      <form onSubmit={handleSubmit} className="space-y-5">
        {/* ── Check cards ── */}
        <div className="space-y-2">
          <Label>Check</Label>
          <div className="grid grid-cols-3 gap-2">
            {CHECK_CARDS.map((c) => {
              const active = selectedCheckName === c.value
              return (
                <button
                  key={c.value}
                  type="button"
                  onClick={() => setSelectedCheckName(c.value)}
                  className={cn(
                    'flex flex-col items-start gap-1.5 rounded-lg border p-3 text-left transition-all',
                    active
                      ? 'border-primary bg-primary/10 shadow-sm'
                      : 'border-border bg-muted/20 hover:bg-muted/40 hover:border-border/80',
                  )}
                >
                  <HugeiconsIcon
                    icon={c.icon}
                    strokeWidth={1.5}
                    className={cn('size-4', active ? 'text-primary' : c.color)}
                  />
                  <span className={cn('text-xs font-medium leading-tight', active ? 'text-primary' : 'text-foreground')}>
                    {c.label}
                  </span>
                </button>
              )
            })}
          </div>
        </div>

        {/* ── Time window selector — for utilization checks ── */}
        {showTimeWindow && (
          <div className="space-y-1.5">
            <Label>Time Window</Label>
            <div className="flex gap-1.5">
              {TIME_WINDOWS.map((tw) => (
                <button
                  key={tw.value}
                  type="button"
                  onClick={() => setWindowHours(tw.value)}
                  className={cn(
                    'rounded-md border px-3 py-1.5 text-xs font-medium transition-colors',
                    windowHours === tw.value
                      ? 'border-primary bg-primary/10 text-primary'
                      : 'border-border bg-muted/30 text-muted-foreground hover:border-primary/50',
                  )}
                >
                  {tw.label}
                </button>
              ))}
            </div>
            <p className="text-[11px] text-muted-foreground">
              Analyze metrics from the last {windowHours} hour{windowHours !== 1 ? 's' : ''}
            </p>
          </div>
        )}

        {/* ── Accounts grouped by customer (collapsible + search) ── */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <Label>
              Accounts
              <span className="ml-1.5 text-xs font-normal text-muted-foreground">
                {selectedAccountIds.length === 0
                  ? '— all accounts will be checked'
                  : `— ${selectedAccountIds.length} selected`}
              </span>
            </Label>
            {selectedAccountIds.length > 0 && (
              <button
                type="button"
                onClick={() => setSelectedAccountIds([])}
                className="text-xs text-muted-foreground hover:text-foreground transition-colors"
              >
                Clear
              </button>
            )}
          </div>

          {/* Search */}
          {hasCustomers && (
            <Input
              placeholder="Search accounts or customers…"
              value={accountSearch}
              onChange={(e) => setAccountSearch(e.target.value)}
              className="h-8 text-xs"
            />
          )}

          {!hasCustomers && (
            <p className="text-xs text-muted-foreground">
              No customers available.{' '}
              <Link href="/customers" className="underline underline-offset-2 hover:text-foreground">
                Add one in Customers
              </Link>
            </p>
          )}

          <div className="space-y-1">
            {visibleCustomers.map((customer) => {
              if (customer.accounts.length === 0) return null
              const accIds = customer.accounts.map((a) => a.id)
              const allChecked = accIds.every((id) => selectedAccountIds.includes(id))
              const someChecked = accIds.some((id) => selectedAccountIds.includes(id))
              const expanded = isExpanded(customer.id)
              const selectedCount = accIds.filter((id) => selectedAccountIds.includes(id)).length

              return (
                <div key={customer.id} className="rounded-md border border-border/50 overflow-hidden">
                  {/* Customer header — click to expand/collapse, checkbox toggles all */}
                  <div className="flex items-center gap-2 px-3 py-1.5 bg-muted/30 hover:bg-muted/40 transition-colors">
                    <button
                      type="button"
                      onClick={() => toggleAllInCustomer(accIds)}
                      className={cn(
                        'h-3.5 w-3.5 rounded-sm shrink-0 border flex items-center justify-center',
                        allChecked
                          ? 'border-primary bg-primary'
                          : someChecked
                          ? 'border-primary/60 bg-primary/20'
                          : 'border-border bg-background',
                      )}
                    >
                      {(allChecked || someChecked) && (
                        <div className="h-1.5 w-1.5 rounded-sm bg-primary" />
                      )}
                    </button>
                    <button
                      type="button"
                      onClick={() => toggleExpanded(customer.id)}
                      className="flex-1 flex items-center gap-2 text-left"
                    >
                      <span className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">
                        {customer.display_name}
                      </span>
                      {selectedCount > 0 && (
                        <Badge variant="outline" className="text-[9px] px-1 py-0 h-4">
                          {selectedCount}/{accIds.length}
                        </Badge>
                      )}
                      <span className={cn(
                        'ml-auto text-[10px] text-muted-foreground/60 transition-transform',
                        expanded ? 'rotate-180' : '',
                      )}>
                        ▾
                      </span>
                    </button>
                  </div>

                  {/* Account toggle buttons — shown when expanded */}
                  {expanded && (
                    <div className="px-3 py-2 flex flex-wrap gap-1.5 border-t border-border/30">
                      {customer.accounts.map((acc) => {
                        const active = selectedAccountIds.includes(acc.id)
                        return (
                          <button
                            key={acc.id}
                            type="button"
                            onClick={() => toggleAccount(acc.id)}
                            className={cn(
                              'rounded-md border px-2.5 py-1 text-xs font-medium transition-colors',
                              !acc.is_active && 'opacity-50',
                              active
                                ? 'border-primary bg-primary/10 text-primary'
                                : 'border-border bg-muted/20 text-muted-foreground hover:border-primary/50',
                            )}
                          >
                            <span>{acc.display_name}</span>
                            <span className="ml-1 font-mono text-[10px] opacity-60">{acc.account_id}</span>
                          </button>
                        )
                      })}
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        </div>

        {/* ── Alarm names preview (alarm_verification only) ── */}
        {isAlarmCheck && alarmNames.length > 0 && (
          <div className="space-y-2">
            <Label>
              Alarm Names
              <span className="ml-1.5 text-xs font-normal text-muted-foreground">
                ({alarmNames.length} configured — will be verified)
              </span>
            </Label>
            <Input
              placeholder="Search alarms…"
              value={alarmSearch}
              onChange={(e) => setAlarmSearch(e.target.value)}
              className="h-8 text-xs"
            />
            <div className="flex flex-wrap gap-1.5 max-h-28 overflow-y-auto p-2 rounded-md border border-border/60 bg-muted/20">
              {filteredAlarmNames.length === 0 ? (
                <p className="text-xs text-muted-foreground">No alarms match</p>
              ) : (
                filteredAlarmNames.map((name) => (
                  <Badge
                    key={name}
                    variant="outline"
                    className="text-[10px] font-mono px-1.5 py-px h-auto"
                  >
                    {name}
                  </Badge>
                ))
              )}
            </div>
          </div>
        )}

        {isAlarmCheck && selectedAccountIds.length === 0 && (
          <p className="text-xs text-muted-foreground">
            Select accounts above to see their configured alarm names.
          </p>
        )}

        {isAlarmCheck && selectedAccountIds.length > 0 && alarmNames.length === 0 && (
          <p className="text-xs text-amber-400/80">
            No alarm names configured for selected accounts. Add them in the Customers page per account.
          </p>
        )}

        {error && <p className="text-sm text-red-400">{error}</p>}

        <Button type="submit" disabled={isPending || !hasCustomers}>
          {isPending ? 'Running…' : 'Run Check'}
        </Button>
      </form>

      {isPending && <CheckProgress label="Running check…" />}
      {results && <ResultsTable data={results} />}
    </div>
  )
}
