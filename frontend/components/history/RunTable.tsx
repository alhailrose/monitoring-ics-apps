'use client'
// Client component — needs useRouter for pagination
import { useRouter, useSearchParams, usePathname } from 'next/navigation'
import Link from 'next/link'
import { PaginatedTable } from '@/components/common/PaginatedTable'
import { StatusBadge } from '@/components/common/StatusBadge'
import { EmptyState } from '@/components/common/EmptyState'
import { formatDate } from '@/lib/utils'
import type { CheckRunSummary } from '@/lib/types/api'

interface RunTableProps {
  runs: CheckRunSummary[]
  total: number
  page: number
  pageSize: number
}

const COLUMNS = [
  {
    key: 'created_at',
    header: 'Date',
    render: (r: CheckRunSummary) => (
      <span className="text-sm">{formatDate(r.created_at)}</span>
    ),
  },
  {
    key: 'customer',
    header: 'Customer',
    render: (r: CheckRunSummary) => (
      <span className="text-sm font-medium">{r.customer?.display_name ?? '—'}</span>
    ),
  },
  {
    key: 'duration',
    header: 'Duration',
    render: (r: CheckRunSummary) => (
      <span className="text-xs font-mono text-muted-foreground">
        {r.execution_time_seconds != null ? `${r.execution_time_seconds.toFixed(2)}s` : '—'}
      </span>
    ),
  },
  {
    key: 'results',
    header: 'Results',
    render: (r: CheckRunSummary) => (
      <div className="flex items-center gap-2">
        {r.results_summary.ok > 0 && (
          <span className="flex items-center gap-1">
            <StatusBadge status="OK" />
            <span className="text-xs text-muted-foreground">{r.results_summary.ok}</span>
          </span>
        )}
        {r.results_summary.warn > 0 && (
          <span className="flex items-center gap-1">
            <StatusBadge status="WARN" />
            <span className="text-xs text-muted-foreground">{r.results_summary.warn}</span>
          </span>
        )}
        {r.results_summary.error > 0 && (
          <span className="flex items-center gap-1">
            <StatusBadge status="ERROR" />
            <span className="text-xs text-muted-foreground">{r.results_summary.error}</span>
          </span>
        )}
      </div>
    ),
  },
  {
    key: 'actions',
    header: '',
    render: (r: CheckRunSummary) => (
      <Link
        href={`/history/${r.check_run_id}`}
        className="text-xs text-muted-foreground hover:text-foreground hover:underline transition-colors"
      >
        View Details →
      </Link>
    ),
  },
]

export function RunTable({ runs, total, page, pageSize }: RunTableProps) {
  const router = useRouter()
  const searchParams = useSearchParams()
  const pathname = usePathname()

  const handlePageChange = (newPage: number) => {
    const params = new URLSearchParams(searchParams.toString())
    params.set('page', String(newPage))
    router.push(`${pathname}?${params.toString()}`)
  }

  if (runs.length === 0) {
    return <EmptyState title="No runs found" description="Run a check to see history here" />
  }

  return (
    <PaginatedTable
      columns={COLUMNS}
      data={runs}
      total={total}
      page={page}
      pageSize={pageSize}
      onPageChange={handlePageChange}
    />
  )
}
