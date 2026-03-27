'use client'
// Client component — dedicated check for a specific customer (e.g. arbel, huawei)

import { useState, useTransition } from 'react'
import { toast } from 'sonner'
import { runChecks } from '@/app/(dashboard)/checks/actions'
import { ResultsTable } from '@/components/checks/ResultsTable'
import { CheckProgress } from '@/components/checks/CheckProgress'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { HugeiconsIcon } from '@hugeicons/react'
import {
  Database01Icon,
  DollarCircleIcon,
  Alert01Icon,
  ComputerIcon,
  ArchiveRestoreIcon,
} from '@hugeicons/core-free-icons'
import { cn } from '@/lib/utils'
import type { Account, Customer, ExecuteResponse } from '@/lib/types/api'

// Icon map for known check values
const CHECK_ICONS: Record<string, { icon: object; color: string }> = {
  'daily-arbel':        { icon: Database01Icon,    color: 'text-orange-400' },
  'daily-arbel-rds':    { icon: Database01Icon,    color: 'text-orange-400' },
  'daily-arbel-ec2':    { icon: ComputerIcon,      color: 'text-sky-400' },
  'daily-budget':       { icon: DollarCircleIcon,  color: 'text-green-400' },
  'alarm_verification': { icon: Alert01Icon,       color: 'text-red-400' },
  'huawei-ecs-util':    { icon: ComputerIcon,      color: 'text-sky-400' },
  'ec2list':            { icon: ComputerIcon,      color: 'text-sky-400' },
  'backup':             { icon: ArchiveRestoreIcon, color: 'text-emerald-400' },
}

// Checks that support time window selection
const UTILIZATION_CHECKS = new Set(['daily-arbel', 'daily-arbel-rds', 'daily-arbel-ec2', 'huawei-ecs-util'])

const TIME_WINDOWS = [
  { value: 1,  label: '1h' },
  { value: 3,  label: '3h' },
  { value: 12, label: '12h' },
]

interface DedicatedCheckFormProps {
  /**
   * Backend mode sent when running in customer-mode (accounts NOT provided).
   * e.g. "arbel", "huawei", "all".
   * NOT used in account-mode — account-mode always sends mode=single to the backend.
   */
  checkGroup: string
  /** Human-readable label for the check */
  label: string
  /** Description shown above the form */
  description?: string
  /**
   * Flat list of accounts to show as toggle buttons.
   * When provided, the form runs mode=single + account_ids (ignores checkGroup).
   */
  accounts?: Account[]
  /**
   * All customers — used for customer selection mode AND to derive customer_ids in account mode.
   */
  customers?: Customer[]
  /** Available check names for this dedicated check */
  checkNames: Array<{ value: string; label: string }>
}

export function DedicatedCheckForm({
  checkGroup,
  label,
  description,
  accounts,
  customers = [],
  checkNames,
}: DedicatedCheckFormProps) {
  const useAccountMode = Array.isArray(accounts) && accounts.length >= 0

  const [selectedAccountIds, setSelectedAccountIds] = useState<string[]>(
    useAccountMode && accounts && accounts[0] ? [accounts[0].id] : [],
  )
  const [selectedCustomerIds, setSelectedCustomerIds] = useState<string[]>(
    !useAccountMode && customers[0] ? [customers[0].id] : [],
  )
  const [selectedCheckName, setSelectedCheckName] = useState(checkNames[0]?.value ?? '')
  const [windowHours, setWindowHours] = useState(12)
  const [results, setResults] = useState<ExecuteResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [isPending, startTransition] = useTransition()

  const showTimeWindow = UTILIZATION_CHECKS.has(selectedCheckName)

  const toggleAccount = (id: string) => {
    setSelectedAccountIds((prev) =>
      prev.includes(id) ? prev.filter((a) => a !== id) : [...prev, id],
    )
  }

  const toggleCustomer = (id: string) => {
    setSelectedCustomerIds((prev) =>
      prev.includes(id) ? prev.filter((c) => c !== id) : [...prev, id],
    )
  }

  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    const formData = new FormData()
    formData.set('send_slack', 'false')

    if (useAccountMode) {
      // Account-based: always mode=single, pass check_name + account_ids + derived customer_ids
      formData.set('mode', 'single')
      if (selectedCheckName) formData.set('check_name', selectedCheckName)
      selectedAccountIds.forEach((id) => formData.append('account_ids', id))

      // Derive customer_ids from customers whose accounts are selected
      const derivedCustomerIds = customers
        .filter((c) => c.accounts.some((a) => selectedAccountIds.includes(a.id)))
        .map((c) => c.id)
      derivedCustomerIds.forEach((id) => formData.append('customer_ids', id))
    } else {
      // Customer-based: use checkGroup as the backend mode, pass customer_ids
      formData.set('mode', checkGroup)
      if (selectedCheckName) formData.set('check_name', selectedCheckName)
      selectedCustomerIds.forEach((id) => formData.append('customer_ids', id))
    }

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

  const hasSelection = useAccountMode
    ? selectedAccountIds.length > 0
    : selectedCustomerIds.length > 0

  return (
    <div className="space-y-6">
      {description && <p className="text-sm text-muted-foreground">{description}</p>}

      <form onSubmit={handleSubmit} className="space-y-5">
        {/* Check cards — shown when multiple options */}
        {checkNames.length > 1 && (
          <div className="space-y-2">
            <Label>Check</Label>
            <div className="flex flex-wrap gap-2">
              {checkNames.map((c) => {
                const active = selectedCheckName === c.value
                const meta = CHECK_ICONS[c.value]
                return (
                  <button
                    key={c.value}
                    type="button"
                    onClick={() => setSelectedCheckName(c.value)}
                    className={cn(
                      'flex items-center gap-2 rounded-lg border px-3 py-2 text-left transition-all text-xs font-medium',
                      active
                        ? 'border-primary bg-primary/10 text-primary shadow-sm'
                        : 'border-border bg-muted/20 text-foreground hover:bg-muted/40 hover:border-border/80',
                    )}
                  >
                    {meta && (
                      <HugeiconsIcon
                        icon={meta.icon as Parameters<typeof HugeiconsIcon>[0]['icon']}
                        strokeWidth={1.5}
                        className={cn('size-3.5', active ? 'text-primary' : meta.color)}
                      />
                    )}
                    {c.label}
                  </button>
                )
              })}
            </div>
          </div>
        )}

        {/* Time window selector — for utilization checks */}
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

        {/* Account toggle buttons — when accounts prop provided */}
        {useAccountMode && (
          <div className="space-y-1.5">
            <div className="flex items-center justify-between">
              <Label>Accounts</Label>
              {accounts && accounts.length > 0 && (
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => setSelectedAccountIds(accounts.map((a) => a.id))}
                    className="text-xs text-muted-foreground hover:text-foreground transition-colors"
                  >
                    Select All
                  </button>
                  {selectedAccountIds.length > 0 && (
                    <>
                      <span className="text-xs text-muted-foreground">·</span>
                      <button
                        type="button"
                        onClick={() => setSelectedAccountIds([])}
                        className="text-xs text-muted-foreground hover:text-foreground transition-colors"
                      >
                        Clear
                      </button>
                    </>
                  )}
                </div>
              )}
            </div>
            {!accounts || accounts.length === 0 ? (
              <p className="text-xs text-muted-foreground">No accounts available</p>
            ) : (
              <div className="flex flex-wrap gap-2">
                {accounts.map((a) => {
                  const active = selectedAccountIds.includes(a.id)
                  return (
                    <button
                      key={a.id}
                      type="button"
                      onClick={() => toggleAccount(a.id)}
                      className={cn(
                        'rounded-md border px-3 py-1.5 text-xs font-medium transition-colors',
                        !a.is_active && 'opacity-50',
                        active
                          ? 'border-primary bg-primary/10 text-primary'
                          : 'border-border bg-muted/30 text-muted-foreground hover:border-primary/50',
                      )}
                    >
                      <span>{a.display_name}</span>
                      <span className="ml-1.5 font-mono text-[10px] opacity-60">{a.account_id}</span>
                    </button>
                  )
                })}
              </div>
            )}
            <p className="text-xs text-muted-foreground">
              {selectedAccountIds.length === 0
                ? 'Select at least one account'
                : `${selectedAccountIds.length} account${selectedAccountIds.length !== 1 ? 's' : ''} selected`}
            </p>
          </div>
        )}

        {/* Customer toggle buttons — when customers prop used */}
        {!useAccountMode && (
          <div className="space-y-1.5">
            <div className="flex items-center justify-between">
              <Label>Customers</Label>
              {customers.length > 0 && (
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => setSelectedCustomerIds(customers.map((c) => c.id))}
                    className="text-xs text-muted-foreground hover:text-foreground transition-colors"
                  >
                    Select All
                  </button>
                  {selectedCustomerIds.length > 0 && (
                    <>
                      <span className="text-xs text-muted-foreground">·</span>
                      <button
                        type="button"
                        onClick={() => setSelectedCustomerIds([])}
                        className="text-xs text-muted-foreground hover:text-foreground transition-colors"
                      >
                        Clear
                      </button>
                    </>
                  )}
                </div>
              )}
            </div>
            {customers.length === 0 ? (
              <p className="text-xs text-muted-foreground">No customers available</p>
            ) : (
              <div className="flex flex-wrap gap-2">
                {customers.map((c) => {
                  const active = selectedCustomerIds.includes(c.id)
                  return (
                    <button
                      key={c.id}
                      type="button"
                      onClick={() => toggleCustomer(c.id)}
                      className={cn(
                        'rounded-md border px-3 py-1.5 text-xs font-medium transition-colors',
                        active
                          ? 'border-primary bg-primary/10 text-primary'
                          : 'border-border bg-muted/30 text-muted-foreground hover:border-primary/50',
                      )}
                    >
                      {c.display_name}
                    </button>
                  )
                })}
              </div>
            )}
            <p className="text-xs text-muted-foreground">
              {selectedCustomerIds.length === 0
                ? 'Select at least one customer'
                : `${selectedCustomerIds.length} customer${selectedCustomerIds.length !== 1 ? 's' : ''} selected`}
            </p>
          </div>
        )}

        {error && <p className="text-sm text-red-400">{error}</p>}

        <Button type="submit" disabled={isPending || !hasSelection}>
          {isPending ? `Running ${label}…` : `Run ${label}`}
        </Button>
      </form>

      {isPending && <CheckProgress label={`Running ${label}…`} />}
      {results && <ResultsTable data={results} />}
    </div>
  )
}
