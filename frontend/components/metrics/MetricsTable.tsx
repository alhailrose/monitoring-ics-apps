'use client'
// Client component — needs onPageChange callback for PaginatedTable pagination
import { useRouter, useSearchParams, usePathname } from 'next/navigation'
import { PaginatedTable } from '@/components/common/PaginatedTable'
import { EmptyState } from '@/components/common/EmptyState'
import { Badge } from '@/components/ui/badge'
import { cn, formatDateFull } from '@/lib/utils'
import type { MetricSample, MetricStatus } from '@/lib/types/api'

const METRIC_STATUS_STYLES: Record<MetricStatus, string> = {
  ok:    'bg-green-600/20 text-green-400 border-green-600/30',
  warn:  'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
  error: 'bg-red-600/20 text-red-400 border-red-600/30',
}

function MetricStatusBadge({ status }: { status: MetricStatus }) {
  return (
    <Badge className={cn(METRIC_STATUS_STYLES[status])}>
      {status.toUpperCase()}
    </Badge>
  )
}


interface MetricsTableProps {
  metrics: MetricSample[]
  total: number
  page: number
  pageSize: number
}

const ALL_COLUMNS = [
  {
    key: 'customer',
    header: 'Customer',
    render: (m: MetricSample) => (
      <span className="text-xs text-muted-foreground">{m.customer?.display_name}</span>
    ),
  },
  {
    key: 'account',
    header: 'Account',
    render: (m: MetricSample) => (
      <span className="text-xs">{m.account.display_name}</span>
    ),
  },
  {
    key: 'check_name',
    header: 'Check',
    render: (m: MetricSample) => (
      <span className="font-mono text-xs">{m.check_name}</span>
    ),
  },
  {
    key: 'metric_name',
    header: 'Metric',
    render: (m: MetricSample) => (
      <span className="text-xs">{m.metric_name}</span>
    ),
  },
  {
    key: 'resource',
    header: 'Resource',
    render: (m: MetricSample) => (
      <span className="text-xs text-muted-foreground">
        {m.resource_name || m.resource_id}
      </span>
    ),
  },
  {
    key: 'value',
    header: 'Value',
    render: (m: MetricSample) => (
      <span className="font-mono text-xs">
        {m.value_num} {m.unit}
      </span>
    ),
  },
  {
    key: 'status',
    header: 'Status',
    render: (m: MetricSample) => <MetricStatusBadge status={m.metric_status} />,
  },
  {
    key: 'created_at',
    header: 'Collected At',
    render: (m: MetricSample) => (
      <span className="text-xs text-muted-foreground">{formatDateFull(m.created_at)}</span>
    ),
  },
]

export function MetricsTable({ metrics, total, page, pageSize }: MetricsTableProps) {
  const router = useRouter()
  const searchParams = useSearchParams()
  const pathname = usePathname()

  const handlePageChange = (newPage: number) => {
    const params = new URLSearchParams(searchParams.toString())
    params.set('page', String(newPage))
    router.push(`${pathname}?${params.toString()}`)
  }

  // Show Customer column only when results span multiple customers
  const multiCustomer = new Set(metrics.map((m) => m.customer?.id).filter(Boolean)).size > 1
  const columns = multiCustomer
    ? ALL_COLUMNS
    : ALL_COLUMNS.filter((c) => c.key !== 'customer')

  if (metrics.length === 0) {
    return (
      <EmptyState
        title="No metrics"
        description="Run a check to collect metrics"
      />
    )
  }

  return (
    <PaginatedTable
      columns={columns}
      data={metrics}
      total={total}
      page={page}
      pageSize={pageSize}
      onPageChange={handlePageChange}
    />
  )
}
