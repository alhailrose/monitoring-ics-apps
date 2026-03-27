'use client'
// Client component — needs useRouter for pagination
import { useRouter, useSearchParams, usePathname } from 'next/navigation'
import { PaginatedTable } from '@/components/common/PaginatedTable'
import { SeverityBadge } from '@/components/common/SeverityBadge'
import { EmptyState } from '@/components/common/EmptyState'
import { Badge } from '@/components/ui/badge'
import { cn, formatDateFull } from '@/lib/utils'
import type { Finding } from '@/lib/types/api'

function StatusBadge({ status }: { status: string }) {
  if (status === 'resolved') {
    return (
      <Badge variant="outline" className="text-[10px] bg-muted/30 text-muted-foreground border-muted-foreground/20">
        resolved
      </Badge>
    )
  }
  return (
    <Badge variant="outline" className="text-[10px] bg-emerald-500/10 text-emerald-500 border-emerald-500/20">
      active
    </Badge>
  )
}

interface FindingsTableProps {
  findings: Finding[]
  total: number
  page: number
  pageSize: number
}

const ALL_COLUMNS = [
  {
    key: 'customer',
    header: 'Customer',
    render: (f: Finding) => (
      <span className="text-xs text-muted-foreground">{f.customer?.display_name}</span>
    ),
  },
  {
    key: 'account',
    header: 'Account',
    render: (f: Finding) => (
      <span className="text-xs">{f.account.display_name}</span>
    ),
  },
  {
    key: 'check_name',
    header: 'Check',
    render: (f: Finding) => (
      <span className="font-mono text-xs">{f.check_name}</span>
    ),
  },
  {
    key: 'severity',
    header: 'Severity',
    render: (f: Finding) => <SeverityBadge severity={f.severity} />,
  },
  {
    key: 'title',
    header: 'Title',
    render: (f: Finding) => (
      <div>
        <p className={cn('text-xs', f.status === 'resolved' && 'text-muted-foreground line-through decoration-muted-foreground/50')}>
          {f.title}
        </p>
        {f.description && (
          <p className="text-[10px] text-muted-foreground mt-0.5 line-clamp-1">{f.description}</p>
        )}
      </div>
    ),
  },
  {
    key: 'status',
    header: 'Status',
    render: (f: Finding) => <StatusBadge status={f.status ?? 'active'} />,
  },
  {
    key: 'last_seen_at',
    header: 'Timeline',
    render: (f: Finding) => {
      const foundAt = formatDateFull(f.created_at)
      const seenAt = f.last_seen_at ? formatDateFull(f.last_seen_at) : null
      const showLastSeen = Boolean(seenAt && seenAt !== foundAt)

      return (
        <div className="text-xs text-muted-foreground">
          <p>found {foundAt}</p>
          {showLastSeen && <p className="text-[10px] text-muted-foreground/70">last seen {seenAt}</p>}
          {f.status === 'resolved' && f.resolved_at && (
            <p className="text-[10px] text-muted-foreground/60">resolved {formatDateFull(f.resolved_at)}</p>
          )}
        </div>
      )
    },
  },
]

export function FindingsTable({ findings, total, page, pageSize }: FindingsTableProps) {
  const router = useRouter()
  const searchParams = useSearchParams()
  const pathname = usePathname()

  const handlePageChange = (newPage: number) => {
    const params = new URLSearchParams(searchParams.toString())
    params.set('page', String(newPage))
    router.push(`${pathname}?${params.toString()}`)
  }

  // Show Customer column only when results span multiple customers
  const multiCustomer = new Set(findings.map((f) => f.customer?.id).filter(Boolean)).size > 1
  const columns = multiCustomer
    ? ALL_COLUMNS
    : ALL_COLUMNS.filter((c) => c.key !== 'customer')

  if (findings.length === 0) {
    return <EmptyState title="No findings" description="All checks are clean" />
  }

  return (
    <PaginatedTable
      columns={columns}
      data={findings}
      total={total}
      page={page}
      pageSize={pageSize}
      onPageChange={handlePageChange}
    />
  )
}
