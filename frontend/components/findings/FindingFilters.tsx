'use client'
// Client component — updates URL search params on filter change
import { useRouter, useSearchParams, usePathname } from 'next/navigation'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'

const SEVERITY_OPTIONS = ['ALL', 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'INFO', 'ALARM'] as const

const CHECK_LABELS: Record<string, string> = {
  'ec2_utilization':  'Utilization (EC2)',
  'daily-arbel-rds':  'Utilization (RDS)',
  'daily-arbel-ec2':  'Utilization (EC2 Arbel)',
  'daily-arbel':      'Arbel (RDS + EC2)',
  'guardduty':        'GuardDuty',
  'cloudwatch':       'CloudWatch Alarms',
  'notifications':    'Notifications',
  'backup':           'Backup',
}

// Checks that produce finding_events rows
const FINDING_CHECKS = new Set([
  'ec2_utilization',
  'daily-arbel-rds',
  'daily-arbel-ec2',
  'guardduty',
  'cloudwatch',
  'notifications',
  'backup',
])

interface FindingFiltersProps {
  customerId?: string
  customerChecks?: string[]
}

export function FindingFilters({ customerId: _customerId = '', customerChecks }: FindingFiltersProps) {
  const router = useRouter()
  const searchParams = useSearchParams()
  const pathname = usePathname()

  const severity = searchParams.get('severity') ?? 'ALL'
  const checkName = searchParams.get('check_name') ?? 'ALL'
  const status = searchParams.get('status') ?? 'active'

  const checkOptions = [
    { value: 'ALL', label: 'All Checks' },
    ...(customerChecks && customerChecks.length > 0
      ? customerChecks
          .filter((c) => FINDING_CHECKS.has(c))
          .map((c) => ({ value: c, label: CHECK_LABELS[c] ?? c }))
      : Array.from(FINDING_CHECKS).map((c) => ({ value: c, label: CHECK_LABELS[c] ?? c }))),
  ]

  const update = (key: string, value: string) => {
    const params = new URLSearchParams(searchParams.toString())
    if (value === 'ALL') {
      params.delete(key)
    } else {
      params.set(key, value)
    }
    params.delete('page')
    router.push(`${pathname}?${params.toString()}`)
  }

  return (
    <div className="flex items-center gap-2">
      <Select value={status} onValueChange={(v) => update('status', v)}>
        <SelectTrigger className="w-28" aria-label="Filter by status">
          <SelectValue placeholder="Active" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="active">Active</SelectItem>
          <SelectItem value="resolved">Resolved</SelectItem>
          <SelectItem value="all">All</SelectItem>
        </SelectContent>
      </Select>

      <Select value={severity} onValueChange={(v) => update('severity', v)}>
        <SelectTrigger className="w-36" aria-label="Filter by severity">
          <SelectValue placeholder="Severity" />
        </SelectTrigger>
        <SelectContent>
          {SEVERITY_OPTIONS.map((s) => (
            <SelectItem key={s} value={s}>{s}</SelectItem>
          ))}
        </SelectContent>
      </Select>

      <Select value={checkName} onValueChange={(v) => update('check_name', v)}>
        <SelectTrigger className="w-48" aria-label="Filter by check">
          <SelectValue placeholder="All Checks" />
        </SelectTrigger>
        <SelectContent>
          {checkOptions.map((c) => (
            <SelectItem key={c.value} value={c.value}>{c.label}</SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  )
}
