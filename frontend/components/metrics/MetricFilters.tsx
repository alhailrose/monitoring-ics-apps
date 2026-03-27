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

const DAYS_OPTIONS = [
  { value: '7',  label: '7 days' },
  { value: '14', label: '14 days' },
  { value: '30', label: '30 days' },
  { value: '90', label: '90 days' },
]

// Map check name → display label for metric checks
const CHECK_LABELS: Record<string, string> = {
  'ec2_utilization':  'EC2 Utilization',
  'daily-arbel-rds':  'RDS Utilization (Arbel)',
  'daily-arbel-ec2':  'EC2 Utilization (Arbel)',
  'daily-arbel':      'Arbel Utilization (RDS + EC2)',
}

// Checks that actually produce metric_samples rows
const METRIC_CHECKS = new Set([
  'ec2_utilization',
  'daily-arbel-rds',
  'daily-arbel-ec2',
  'daily-arbel',
])

interface MetricFiltersProps {
  customerId?: string
  customerChecks?: string[]
}

export function MetricFilters({ customerId: _customerId = '', customerChecks }: MetricFiltersProps) {
  const router = useRouter()
  const searchParams = useSearchParams()
  const pathname = usePathname()

  const currentCheck = searchParams.get('check_name') ?? ''
  const currentDays  = searchParams.get('days') ?? '14'

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
      <Select value={currentDays} onValueChange={(v) => updateParam('days', v)}>
        <SelectTrigger className="w-28" aria-label="Time range">
          <SelectValue placeholder="14 days" />
        </SelectTrigger>
        <SelectContent>
          {DAYS_OPTIONS.map((o) => (
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
