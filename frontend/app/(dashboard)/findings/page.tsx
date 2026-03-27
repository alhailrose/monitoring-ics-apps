// Server Component — fetches data server-side, passes to client components
import { getToken } from '@/lib/server-token'
import { getCustomers } from '@/lib/api/customers'
import { getFindings } from '@/lib/api/findings'
import { PageHeader } from '@/components/common/PageHeader'
import { CustomerSelector } from '@/components/common/CustomerSelector'
import { FindingsTable } from '@/components/findings/FindingsTable'
import { FindingFilters } from '@/components/findings/FindingFilters'
import type { FindingSeverity, FindingStatus } from '@/lib/types/api'

const PAGE_SIZE = 20

interface SearchParams {
  customer_id?: string
  severity?: string
  check_name?: string
  status?: string
  page?: string
}

export default async function FindingsPage({
  searchParams,
}: {
  searchParams: Promise<SearchParams>
}) {
  const params = await searchParams
  const token = await getToken()

  const customers = await getCustomers(token).catch(() => [])
  const customerId = params.customer_id ?? ''
  const customer = customers.find((c) => c.id === customerId)
  const customerChecks = customer?.checks
  const page = Math.max(1, Number(params.page ?? 1))
  const offset = (page - 1) * PAGE_SIZE

  const checkName = params.check_name && params.check_name.toUpperCase() !== 'ALL'
    ? params.check_name : undefined
  const severity = params.severity && params.severity.toUpperCase() !== 'ALL'
    ? params.severity as FindingSeverity : undefined
  const status = (params.status === 'all' ? 'all' : (params.status as FindingStatus | undefined)) ?? 'active'

  const findingsData = await getFindings(
    {
      customer_id: customerId || undefined,
      severity,
      check_name: checkName,
      status,
      limit: PAGE_SIZE,
      offset,
    },
    token,
  ).catch(() => ({ items: [], total: 0 }))

  return (
    <div className="space-y-6 p-6">
      <PageHeader
        title="Findings"
        description="Issues detected across check runs"
        actions={
          <div className="flex items-center gap-2">
            <CustomerSelector customers={customers} customerId={customerId} allowAll />
            <FindingFilters customerId={customerId} customerChecks={customerChecks} />
          </div>
        }
      />
      <FindingsTable
        findings={findingsData.items}
        total={findingsData.total}
        page={page}
        pageSize={PAGE_SIZE}
      />
    </div>
  )
}
