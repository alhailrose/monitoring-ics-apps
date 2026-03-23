'use client'
// Client component — needs useRouter for pagination
import { useRouter, useSearchParams, usePathname } from 'next/navigation'
import { PaginatedTable } from '@/components/common/PaginatedTable'
import { SeverityBadge } from '@/components/common/SeverityBadge'
import { EmptyState } from '@/components/common/EmptyState'
import { formatDate } from '@/lib/utils'
import type { Finding } from '@/lib/types/api'

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
      <span className="text-xs text-muted-foreground">{f.customer.display_name}</span>
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
      <span className="text-xs">{f.title}</span>
    ),
  },
  {
    key: 'created_at',
    header: 'Date',
    render: (f: Finding) => (
      <span className="text-xs text-muted-foreground">{formatDate(f.created_at)}</span>
    ),
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
  const multiCustomer = new Set(findings.map((f) => f.customer.id)).size > 1
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
