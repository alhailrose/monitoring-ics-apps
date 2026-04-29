'use client'

import { useState, useMemo, useTransition, useEffect, useRef } from 'react'
import { toast } from 'sonner'
import { runChecks } from '@/app/(dashboard)/checks/actions'
import { ResultsTable } from '@/components/checks/ResultsTable'
import { CheckProgress } from '@/components/checks/CheckProgress'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Input } from '@/components/ui/input'
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
  CodeSimpleIcon,
  ContainerIcon,
  FolderCloudIcon,
  CellularNetworkIcon,
  Key01Icon,
} from '@hugeicons/core-free-icons'
import Link from 'next/link'
import { cn } from '@/lib/utils'
import type { Customer, ExecuteResponse } from '@/lib/types/api'

interface Ec2Instance {
  instance_id: string
  name: string
  instance_type: string
  region: string
  platform: string
}

interface AccountSnapshot {
  loading: boolean
  instances: Ec2Instance[]
  noData: boolean  // discovery never run
}

type SnapshotMap = Record<string, AccountSnapshot>  // key = account DB id

const CHECK_CARDS = [
  { value: 'guardduty',          label: 'GuardDuty',          icon: Shield01Icon,       color: 'text-blue-400' },
  { value: 'cloudwatch',         label: 'CloudWatch',          icon: Chart01Icon,        color: 'text-cyan-400' },
  { value: 'notifications',      label: 'Notifications',       icon: Notification01Icon, color: 'text-violet-400' },
  { value: 'backup',             label: 'Backup',              icon: ArchiveRestoreIcon, color: 'text-emerald-400' },
  { value: 'cost',               label: 'Cost',                icon: DollarCircleIcon,   color: 'text-amber-400' },
  { value: 'daily-arbel-rds',    label: 'RDS Utilization',     icon: Database01Icon,     color: 'text-orange-400' },
  { value: 'ec2_utilization',    label: 'EC2 Utilization',     icon: ComputerIcon,       color: 'text-sky-400' },
  { value: 'alarm_verification', label: 'Alarm Verification',  icon: Alert01Icon,        color: 'text-red-400' },
  { value: 'daily-budget',       label: 'Daily Budget',        icon: DollarCircleIcon,   color: 'text-green-400' },
  { value: 'lambda',             label: 'Lambda',              icon: CodeSimpleIcon,      color: 'text-yellow-400' },
  { value: 'ecs',                label: 'ECS Services',        icon: ContainerIcon,       color: 'text-teal-400' },
  { value: 's3',                 label: 'S3 Buckets',          icon: FolderCloudIcon,     color: 'text-orange-300' },
  { value: 'vpc',                label: 'VPC Security',        icon: CellularNetworkIcon, color: 'text-indigo-400' },
  { value: 'iam',                label: 'IAM Hygiene',         icon: Key01Icon,           color: 'text-rose-400' },
]

// Checks that support time window selection
const UTILIZATION_CHECKS = new Set(['daily-arbel-rds', 'ec2_utilization'])

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
  const handleCheckChange = (val: string) => { setSelectedCheckName(val); setSelectedAlarmNames([]) }
  const [windowHours, setWindowHours] = useState(12)
  const [alarmSearch, setAlarmSearch] = useState('')
  const [selectedAlarmNames, setSelectedAlarmNames] = useState<string[]>([])
  const [accountSearch, setAccountSearch] = useState('')
  const [expandedCustomers, setExpandedCustomers] = useState<Set<string>>(
    () => new Set(customers.map((c) => c.id)),
  )
  const [results, setResults] = useState<ExecuteResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [isPending, startTransition] = useTransition()
  const resultAnchorRef = useRef<HTMLDivElement | null>(null)

  // EC2 instance selection (for ec2_utilization)
  const [snapshotMap, setSnapshotMap] = useState<SnapshotMap>({})
  const [selectedInstanceIds, setSelectedInstanceIds] = useState<string[]>([])
  const [instanceSearch, setInstanceSearch] = useState('')
  const fetchedRef = useRef<Set<string>>(new Set())

  const isEc2Check = selectedCheckName === 'ec2_utilization'

  // Fetch discovery snapshots when ec2_utilization is selected and accounts change
  useEffect(() => {
    if (!isEc2Check) return
    const toFetch = selectedAccountIds.filter((id) => !fetchedRef.current.has(id))
    if (toFetch.length === 0) return

    toFetch.forEach((accId) => {
      fetchedRef.current.add(accId)
      setSnapshotMap((prev) => ({ ...prev, [accId]: { loading: true, instances: [], noData: false } }))
      fetch(`/api/discovery-snapshot/${accId}`)
        .then((r) => r.json())
        .then((data) => {
          const instances: Ec2Instance[] = (data?.snapshot?.ec2_instances ?? [])
          setSnapshotMap((prev) => ({
            ...prev,
            [accId]: { loading: false, instances, noData: instances.length === 0 && !data?.snapshot },
          }))
        })
        .catch(() => {
          setSnapshotMap((prev) => ({ ...prev, [accId]: { loading: false, instances: [], noData: true } }))
        })
    })
  }, [isEc2Check, selectedAccountIds])

  // Reset instance selection when check type or accounts change
  useEffect(() => {
    setSelectedInstanceIds([])
    setInstanceSearch('')
  }, [selectedCheckName, selectedAccountIds])

  useEffect(() => {
    if (!results) return
    if (typeof resultAnchorRef.current?.scrollIntoView === 'function') {
      resultAnchorRef.current.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }
  }, [results])

  const toggleInstance = (id: string) => {
    setSelectedInstanceIds((prev) => prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id])
  }

  const showTimeWindow = UTILIZATION_CHECKS.has(selectedCheckName)

  const toggleAccount = (id: string) => {
    setSelectedAccountIds((prev) =>
      prev.includes(id) ? prev.filter((a) => a !== id) : [...prev, id],
    )
    setSelectedAlarmNames([]) // reset alarm filter when accounts change
  }

  const toggleAlarmName = (name: string) => {
    setSelectedAlarmNames((prev) =>
      prev.includes(name) ? prev.filter((n) => n !== name) : [...prev, name],
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

  const isExpanded = (customerId: string) => {
    if (accountSearch.trim()) return true
    return expandedCustomers.has(customerId)
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

    const accountsToRun = (selectedAccountIds.length > 0
      ? allAccounts.filter((a) => selectedAccountIds.includes(a.id))
      : allAccounts
    ).filter((a) => a.is_active)

    if (isAlarmCheck && selectedAccountIds.length > 0 && alarmNames.length === 0) {
      const msg = 'Selected accounts have no configured alarm names. Configure alarms in Customers first.'
      setError(msg)
      toast.error('Cannot run check', { description: msg })
      return
    }

    if (isEc2Check && selectedAccountIds.length > 0) {
      const notDiscovered = accountsToRun.filter((a) => {
        const snap = snapshotMap[a.id]
        return !snap || (!snap.loading && snap.noData)
      })
      if (notDiscovered.length > 0) {
        const msg = `Instance discovery missing for: ${notDiscovered.map((a) => a.display_name).join(', ')}`
        setError(msg)
        toast.error('Cannot run check', { description: msg })
        return
      }
    }

    const formData = new FormData()
    formData.set('mode', 'single')
    formData.set('send_slack', 'false')
    formData.set('check_name', selectedCheckName)
    derivedCustomerIds.forEach((id) => formData.append('customer_ids', id))
    selectedAccountIds.forEach((id) => formData.append('account_ids', id))

    // Build check_params
    const checkParams: Record<string, unknown> = {}
    if (showTimeWindow) {
      if (selectedCheckName === 'ec2_utilization') checkParams.util_hours = windowHours
      else checkParams.window_hours = windowHours
    }
    // Pass specific instance list for ec2_utilization if user selected instances
    if (isEc2Check && selectedInstanceIds.length > 0) {
      const allInstances = Object.values(snapshotMap).flatMap((s) => s.instances)
      const picked = allInstances.filter((i) => selectedInstanceIds.includes(i.instance_id))
      if (picked.length > 0) {
        checkParams.instance_list = picked.map((i) => ({
          instance_id: i.instance_id,
          name: i.name,
          os_type: i.platform === 'windows' ? 'windows' : 'linux',
          instance_type: i.instance_type,
          region: i.region,
        }))
      }
    }
    // Per-account alarm name overrides for alarm_verification
    if (isAlarmCheck && selectedAlarmNames.length > 0) {
      const accountAlarmNames: Record<string, string[]> = {}
      for (const acc of targetAccounts) {
        const filtered = (acc.alarm_names ?? []).filter((n) => selectedAlarmNames.includes(n))
        if (filtered.length > 0) accountAlarmNames[acc.id] = filtered
      }
      if (Object.keys(accountAlarmNames).length > 0) {
        checkParams.account_alarm_names = accountAlarmNames
      }
    }
    if (Object.keys(checkParams).length > 0) {
      formData.set('check_params', JSON.stringify(checkParams))
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
  const latestRunId = results?.check_run_id ?? results?.check_runs?.[0]?.check_run_id ?? null
  const preflightAccounts = (selectedAccountIds.length > 0
    ? allAccounts.filter((a) => selectedAccountIds.includes(a.id))
    : allAccounts
  ).filter((a) => a.is_active)
  const alarmConfigMissing = isAlarmCheck && selectedAccountIds.length > 0 && alarmNames.length === 0
  const discoveryMissing = isEc2Check && selectedAccountIds.length > 0
    ? preflightAccounts.filter((a) => {
        const snap = snapshotMap[a.id]
        return !snap || (!snap.loading && snap.noData)
      })
    : []
  const runBlockedReason = !hasCustomers
    ? 'No customers available'
    : alarmConfigMissing
      ? 'Selected accounts have no alarm names configured'
      : discoveryMissing.length > 0
        ? `Instance discovery missing for ${discoveryMissing.length} account(s)`
        : null

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
                  onClick={() => handleCheckChange(c.value)}
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

        {/* ── Account selector ── */}
        <div className="space-y-1.5">
          <Label>Accounts</Label>

          {!hasCustomers ? (
            <p className="text-xs text-muted-foreground">
              No customers available.{' '}
              <Link href="/customers" className="underline underline-offset-2 hover:text-foreground">
                Add one in Customers
              </Link>
            </p>
          ) : (
            <div className="rounded-lg border border-border/60 overflow-hidden text-sm">

              {/* ── Selected chips ── */}
              {selectedAccountIds.length > 0 && (
                <div className="px-3 pt-2.5 pb-2 border-b border-border/40 bg-primary/[0.03]">
                  <div className="flex flex-wrap gap-1.5">
                    {allAccounts
                      .filter((a) => selectedAccountIds.includes(a.id))
                      .map((a) => (
                        <button
                          key={a.id}
                          type="button"
                          onClick={() => toggleAccount(a.id)}
                          className="inline-flex items-center gap-1 rounded border border-primary/25 bg-primary/10 px-2 py-0.5 text-[11px] font-medium text-primary transition-colors hover:bg-primary/20"
                        >
                          {a.display_name}
                          <span className="text-primary/50 text-[10px] leading-none">×</span>
                        </button>
                      ))}
                    <button
                      type="button"
                      onClick={() => setSelectedAccountIds([])}
                      className="ml-auto self-center text-[10px] text-muted-foreground hover:text-foreground transition-colors"
                    >
                      Clear all
                    </button>
                  </div>
                </div>
              )}

              {/* ── Search ── */}
              <div className="relative border-b border-border/40">
                <input
                  placeholder="Cari akun atau customer…"
                  value={accountSearch}
                  onChange={(e) => setAccountSearch(e.target.value)}
                  className="w-full bg-transparent px-3 py-2 text-xs outline-none placeholder:text-muted-foreground/40"
                />
                {accountSearch && (
                  <button
                    type="button"
                    onClick={() => setAccountSearch('')}
                    className="absolute right-2.5 top-1/2 -translate-y-1/2 text-xs text-muted-foreground/50 hover:text-muted-foreground transition-colors"
                  >
                    ×
                  </button>
                )}
              </div>

              {/* ── Account list ── */}
              <div className="max-h-60 overflow-y-auto">
                {visibleCustomers.length === 0 ? (
                  <p className="px-3 py-5 text-center text-xs text-muted-foreground">
                    Tidak ada akun yang cocok
                  </p>
                ) : (
                  visibleCustomers.map((customer) => {
                    if (customer.accounts.length === 0) return null
                    const accIds = customer.accounts.map((a) => a.id)
                    const allChecked = accIds.every((id) => selectedAccountIds.includes(id))
                    const someChecked = accIds.some((id) => selectedAccountIds.includes(id))
                    const selectedCount = accIds.filter((id) => selectedAccountIds.includes(id)).length
                    const expanded = isExpanded(customer.id)

                    return (
                      <div key={customer.id}>
                        {/* Customer group header */}
                        <div className="flex items-center gap-2 sticky top-0 z-10 border-b border-border/20 bg-muted/30 px-3 py-1.5">
                          {/* Select-all checkbox */}
                          <button
                            type="button"
                            onClick={() => toggleAllInCustomer(accIds)}
                            className={cn(
                              'h-3.5 w-3.5 shrink-0 rounded border flex items-center justify-center transition-colors',
                              allChecked
                                ? 'border-primary bg-primary'
                                : someChecked
                                ? 'border-primary'
                                : 'border-border/60 hover:border-border',
                            )}
                          >
                            {allChecked && (
                              <svg className="size-2 text-primary-foreground" viewBox="0 0 10 8" fill="none" stroke="currentColor" strokeWidth={3} strokeLinecap="round" strokeLinejoin="round">
                                <path d="M1 4l2.5 2.5L9 1" />
                              </svg>
                            )}
                            {someChecked && !allChecked && (
                              <div className="h-px w-2 bg-primary" />
                            )}
                          </button>

                          <span className="flex-1 text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">
                            {customer.display_name}
                          </span>

                          {someChecked && (
                            <span className="text-[10px] text-primary/70 tabular-nums">
                              {selectedCount}/{accIds.length}
                            </span>
                          )}

                          <button
                            type="button"
                            onClick={() => toggleExpanded(customer.id)}
                            className="text-[10px] text-muted-foreground/40 hover:text-muted-foreground transition-colors select-none"
                          >
                            {expanded ? '▴' : '▾'}
                          </button>
                        </div>

                        {/* Account rows */}
                        {expanded && customer.accounts.map((acc) => {
                          const active = selectedAccountIds.includes(acc.id)
                          return (
                            <button
                              key={acc.id}
                              type="button"
                              onClick={() => acc.is_active ? toggleAccount(acc.id) : undefined}
                              disabled={!acc.is_active}
                              className={cn(
                                'flex w-full items-center gap-2.5 border-b border-border/10 px-3 py-2 text-left last:border-0 transition-colors',
                                !acc.is_active
                                  ? 'cursor-not-allowed opacity-35'
                                  : active
                                  ? 'bg-primary/5 hover:bg-primary/8'
                                  : 'hover:bg-muted/20',
                              )}
                            >
                              {/* Row checkbox */}
                              <div className={cn(
                                'h-3.5 w-3.5 shrink-0 rounded border flex items-center justify-center transition-colors',
                                active ? 'border-primary bg-primary' : 'border-border/40',
                              )}>
                                {active && (
                                  <svg className="size-2 text-primary-foreground" viewBox="0 0 10 8" fill="none" stroke="currentColor" strokeWidth={3} strokeLinecap="round" strokeLinejoin="round">
                                    <path d="M1 4l2.5 2.5L9 1" />
                                  </svg>
                                )}
                              </div>

                              <span className={cn(
                                'flex-1 text-xs leading-tight',
                                active ? 'font-medium text-foreground' : 'text-muted-foreground',
                              )}>
                                {acc.display_name}
                              </span>

                              <span className="shrink-0 font-mono text-[10px] text-muted-foreground/35">
                                {acc.account_id}
                              </span>
                            </button>
                          )
                        })}
                      </div>
                    )
                  })
                )}
              </div>

              {/* ── Footer ── */}
              <div className="flex items-center justify-between border-t border-border/30 bg-muted/10 px-3 py-1.5">
                <span className="text-[10px] text-muted-foreground">
                  {selectedAccountIds.length === 0
                    ? `${allAccounts.length} akun tersedia — semua akan dicek`
                    : `${selectedAccountIds.length} dari ${allAccounts.length} dipilih`}
                </span>
                <button
                  type="button"
                  onClick={() => setSelectedAccountIds(allAccounts.map((a) => a.id))}
                  className="text-[10px] text-muted-foreground hover:text-foreground transition-colors"
                >
                  Pilih semua
                </button>
              </div>
            </div>
          )}
        </div>

        {/* ── Alarm names (alarm_verification only) — selectable ── */}
        {isAlarmCheck && alarmNames.length > 0 && (
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <Label>
                Alarm Names
                <span className="ml-1.5 text-xs font-normal text-muted-foreground">
                  {selectedAlarmNames.length === 0
                    ? `— semua ${alarmNames.length} akan dicek`
                    : `— ${selectedAlarmNames.length} dari ${alarmNames.length} dipilih`}
                </span>
              </Label>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => setSelectedAlarmNames([...alarmNames])}
                  className="text-xs text-muted-foreground hover:text-foreground transition-colors"
                >
                  Select All
                </button>
                {selectedAlarmNames.length > 0 && (
                  <>
                    <span className="text-xs text-muted-foreground">·</span>
                    <button
                      type="button"
                      onClick={() => setSelectedAlarmNames([])}
                      className="text-xs text-muted-foreground hover:text-foreground transition-colors"
                    >
                      Clear
                    </button>
                  </>
                )}
              </div>
            </div>
            <Input
              placeholder="Search alarms…"
              value={alarmSearch}
              onChange={(e) => setAlarmSearch(e.target.value)}
              className="h-8 text-xs"
            />
            <div className="flex flex-wrap gap-1.5 max-h-36 overflow-y-auto p-2 rounded-md border border-border/60 bg-muted/20">
              {filteredAlarmNames.length === 0 ? (
                <p className="text-xs text-muted-foreground">No alarms match</p>
              ) : (
                filteredAlarmNames.map((name) => {
                  const selected = selectedAlarmNames.includes(name)
                  return (
                    <button
                      key={name}
                      type="button"
                      onClick={() => toggleAlarmName(name)}
                      className={cn(
                        'rounded-md border px-2 py-0.5 text-[10px] font-mono transition-colors',
                        selected
                          ? 'border-primary bg-primary/10 text-primary'
                          : 'border-border/60 bg-background text-muted-foreground hover:border-primary/50 hover:text-foreground',
                      )}
                    >
                      {name}
                    </button>
                  )
                })
              )}
            </div>
            {selectedAlarmNames.length === 0 && (
              <p className="text-[11px] text-muted-foreground">
                Klik alarm untuk filter — kosong berarti cek semua.
              </p>
            )}
          </div>
        )}

        {isAlarmCheck && selectedAccountIds.length === 0 && (
          <p className="text-xs text-muted-foreground">
            Select accounts above to see their configured alarm names.
          </p>
        )}

        {/* ── EC2 instance selector (ec2_utilization only) ── */}
        {isEc2Check && selectedAccountIds.length > 0 && (() => {
          const activeAccounts = allAccounts.filter((a) => selectedAccountIds.includes(a.id))
          const allInstances = activeAccounts.flatMap((a) => {
            const snap = snapshotMap[a.id]
            return (snap?.instances ?? []).map((i) => ({ ...i, _accName: a.display_name, _accId: a.id }))
          })
          const notDiscovered = activeAccounts.filter((a) => {
            const snap = snapshotMap[a.id]
            return !snap || (!snap.loading && snap.noData)
          })
          const loading = activeAccounts.some((a) => snapshotMap[a.id]?.loading)
          const filteredInstances = instanceSearch.trim()
            ? allInstances.filter((i) =>
                i.name.toLowerCase().includes(instanceSearch.toLowerCase()) ||
                i.instance_id.toLowerCase().includes(instanceSearch.toLowerCase()) ||
                i.region.toLowerCase().includes(instanceSearch.toLowerCase()),
              )
            : allInstances

          return (
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <Label>
                  EC2 Instances
                  <span className="ml-1.5 text-xs font-normal text-muted-foreground">
                    {selectedInstanceIds.length === 0
                      ? `— semua ${allInstances.length} akan dicek`
                      : `— ${selectedInstanceIds.length} dari ${allInstances.length} dipilih`}
                  </span>
                </Label>
                <div className="flex items-center gap-2">
                  <button
                    type="button"
                    onClick={() => setSelectedInstanceIds(allInstances.map((i) => i.instance_id))}
                    className="text-xs text-muted-foreground hover:text-foreground transition-colors"
                  >
                    Select All
                  </button>
                  {selectedInstanceIds.length > 0 && (
                    <>
                      <span className="text-xs text-muted-foreground">·</span>
                      <button
                        type="button"
                        onClick={() => setSelectedInstanceIds([])}
                        className="text-xs text-muted-foreground hover:text-foreground transition-colors"
                      >
                        Clear
                      </button>
                    </>
                  )}
                </div>
              </div>

              {notDiscovered.length > 0 && (
                <div className="rounded border border-amber-500/30 bg-amber-950/20 px-3 py-2 text-xs text-amber-400/90">
                  Instance belum di-discovery:{' '}
                  <span className="font-medium">{notDiscovered.map((a) => a.display_name).join(', ')}</span>
                  . Jalankan <span className="font-mono">Discover Full</span> di halaman Customers terlebih dahulu.
                </div>
              )}

              {loading && (
                <p className="text-xs text-muted-foreground animate-pulse">Memuat daftar instance…</p>
              )}

              {!loading && allInstances.length > 0 && (
                <>
                  <Input
                    placeholder="Cari nama, instance ID, atau region…"
                    value={instanceSearch}
                    onChange={(e) => setInstanceSearch(e.target.value)}
                    className="h-8 text-xs"
                  />
                  <div className="flex flex-col gap-0.5 max-h-48 overflow-y-auto rounded-md border border-border/60 bg-muted/20 p-1.5">
                    {filteredInstances.length === 0 ? (
                      <p className="text-xs text-muted-foreground px-1">Tidak ada instance yang cocok</p>
                    ) : (
                      filteredInstances.map((inst) => {
                        const selected = selectedInstanceIds.includes(inst.instance_id)
                        return (
                          <button
                            key={inst.instance_id}
                            type="button"
                            onClick={() => toggleInstance(inst.instance_id)}
                            className={cn(
                              'flex items-center gap-2.5 rounded px-2 py-1.5 text-left transition-colors',
                              selected ? 'bg-primary/10' : 'hover:bg-muted/40',
                            )}
                          >
                            <div className={cn(
                              'h-3.5 w-3.5 shrink-0 rounded border flex items-center justify-center transition-colors',
                              selected ? 'border-primary bg-primary' : 'border-border/40',
                            )}>
                              {selected && (
                                <svg className="size-2 text-primary-foreground" viewBox="0 0 10 8" fill="none" stroke="currentColor" strokeWidth={3} strokeLinecap="round" strokeLinejoin="round">
                                  <path d="M1 4l2.5 2.5L9 1" />
                                </svg>
                              )}
                            </div>
                            <span className={cn('flex-1 text-xs', selected ? 'font-medium text-foreground' : 'text-muted-foreground')}>
                              {inst.name !== '-' ? inst.name : inst.instance_id}
                            </span>
                            <span className="shrink-0 font-mono text-[10px] text-muted-foreground/50">{inst.instance_type}</span>
                            <span className="shrink-0 font-mono text-[10px] text-muted-foreground/35">{inst.region}</span>
                            {activeAccounts.length > 1 && (
                              <span className="shrink-0 text-[10px] text-muted-foreground/35">{inst._accName}</span>
                            )}
                          </button>
                        )
                      })
                    )}
                  </div>
                  {selectedInstanceIds.length === 0 && (
                    <p className="text-[11px] text-muted-foreground">
                      Klik instance untuk filter — kosong berarti cek semua.
                    </p>
                  )}
                </>
              )}
            </div>
          )
        })()}

        {isAlarmCheck && selectedAccountIds.length > 0 && alarmNames.length === 0 && (
          <p className="text-xs text-amber-400/80">
            No alarm names configured for selected accounts. Add them in the Customers page per account.
          </p>
        )}

        {error && <p className="text-sm text-red-400">{error}</p>}

        <Button type="submit" disabled={isPending || !!runBlockedReason}>
          {isPending ? 'Running…' : 'Run Check'}
        </Button>
        {runBlockedReason && (
          <p className="text-xs text-amber-300">Run blocked: {runBlockedReason}</p>
        )}
      </form>

      {isPending && <CheckProgress label="Running check…" />}
      {results && (
        <div ref={resultAnchorRef} className="space-y-3">
          <div className="rounded-md border border-border/60 bg-muted/20 px-3 py-2">
            <p className="text-xs text-muted-foreground">
              Run completed. Review the results below.
            </p>
            {latestRunId ? (
              <Link href={`/history?run=${latestRunId}`} className="text-xs font-medium underline underline-offset-2">
                View latest run
              </Link>
            ) : null}
          </div>
          <ResultsTable data={results} />
        </div>
      )}
    </div>
  )
}
