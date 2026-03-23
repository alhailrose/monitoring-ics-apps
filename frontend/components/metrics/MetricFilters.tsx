'use client'
// Client component — uses useRouter/useSearchParams to update URL filters

import { useRouter, useSearchParams, usePathname } from 'next/navigation'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'

const STATUS_OPTIONS = [
  { value: 'all', label: 'All Statuses' },
  { value: 'ok', label: 'OK' },
  { value: 'warn', label: 'Warn' },
  { value: 'error', label: 'Error' },
]

// Map check name → display label for metric checks
const CHECK_LABELS: Record<string, string> = {
  'ec2_utilization':  'Utilization (EC2)',
  'daily-arbel-rds':  'Utilization (RDS)',
  'daily-arbel-ec2':  'Utilization (EC2 Arbel)',
  'daily-arbel':      'Arbel (RDS + EC2)',
  'cost':             'Cost Anomalies',
  'cloudwatch':       'CloudWatch Alarms',
  'guardduty':        'GuardDuty',
  'notifications':    'Notifications',
  'backup':           'Backup',
}

// Checks that actually produce metric_samples rows
const METRIC_CHECKS = new Set([
  'ec2_utilization',
  'daily-arbel-rds',
  'daily-arbel-ec2',
  'daily-arbel',
  'cost',
  'cloudwatch',
  'guardduty',
  'notifications',
  'backup',
])

interface MetricFiltersProps {
  customerId?: string
  customerChecks?: string[]
}

export function MetricFilters({ customerId: _customerId = '', customerChecks }: MetricFiltersProps) {
  const router = useRouter()
  const searchParams = useSearchParams()
  const pathname = usePathname()

  const currentStatus = searchParams.get('metric_status') ?? 'all'
  const currentCheck = searchParams.get('check_name') ?? ''

  // Build options from customer's actual checks list, filtered to metric-producing ones
  const checkOptions = customerChecks && customerChecks.length > 0
    ? customerChecks
        .filter((c) => METRIC_CHECKS.has(c))
        .map((c) => ({ value: c, label: CHECK_LABELS[c] ?? c }))
    : Array.from(METRIC_CHECKS).map((c) => ({ value: c, label: CHECK_LABELS[c] ?? c }))

  const updateParam = (key: string, value: string) => {
    const params = new URLSearchParams(searchParams.toString())
    if (!value) {
      params.delete(key)
    } else {
      params.set(key, value)
    }
    params.delete('page')
    router.push(`${pathname}?${params.toString()}`)
  }

  return (
    <div className="flex items-center gap-2">
      <Select value={currentStatus} onValueChange={(v) => updateParam('metric_status', v)}>
        <SelectTrigger className="w-36" aria-label="Filter by status">
          <SelectValue placeholder="All Statuses" />
        </SelectTrigger>
        <SelectContent>
          {STATUS_OPTIONS.map((o) => (
            <SelectItem key={o.value} value={o.value}>
              {o.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      <Select value={currentCheck} onValueChange={(v) => updateParam('check_name', v)}>
        <SelectTrigger className="w-48" aria-label="Filter by check">
          <SelectValue placeholder="Select check..." />
        </SelectTrigger>
        <SelectContent>
          {checkOptions.map((o) => (
            <SelectItem key={o.value} value={o.value}>
              {o.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  )
}
