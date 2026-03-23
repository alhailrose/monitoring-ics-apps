// Server Component — fetches data server-side, passes to client components
import { getToken } from '@/lib/server-token'
import { getCustomers } from '@/lib/api/customers'
import { getHistory } from '@/lib/api/history'
import { PageHeader } from '@/components/common/PageHeader'
import { CustomerSelector } from '@/components/common/CustomerSelector'
import { RunTable } from '@/components/history/RunTable'

const PAGE_SIZE = 20

interface SearchParams {
  customer_id?: string
  page?: string
}

export default async function HistoryPage({
  searchParams,
}: {
  searchParams: Promise<SearchParams>
}) {
  const params = await searchParams
  const token = await getToken()

  const customers = await getCustomers(token).catch(() => [])
  const customerId = params.customer_id ?? ''
  const page = Math.max(1, Number(params.page ?? 1))
  const offset = (page - 1) * PAGE_SIZE

  const historyData = await getHistory(
    { customer_id: customerId || undefined, limit: PAGE_SIZE, offset },
    token,
  ).catch(() => ({ items: [], total: 0 }))

  return (
    <div className="space-y-6 p-6">
      <PageHeader
        title="History"
        description="Past check runs and their results"
        actions={<CustomerSelector customers={customers} customerId={customerId} allowAll />}
      />
      <RunTable
        runs={historyData.items}
        total={historyData.total}
        page={page}
        pageSize={PAGE_SIZE}
      />
    </div>
  )
}
