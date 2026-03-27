// Server Component — fetches data server-side, passes to client components
import { getToken } from '@/lib/server-token'
import { getCustomers } from '@/lib/api/customers'
import { getMetricTimeseries } from '@/lib/api/metrics'
import { PageHeader } from '@/components/common/PageHeader'
import { CustomerSelector } from '@/components/common/CustomerSelector'
import { MetricsCharts } from '@/components/metrics/MetricsCharts'
import { MetricFilters } from '@/components/metrics/MetricFilters'
import { EmptyState } from '@/components/common/EmptyState'

interface SearchParams {
  customer_id?: string
  check_name?: string
  days?: string
}

export default async function MetricsPage({
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
  const checkName = params.check_name
  const days = Math.min(90, Math.max(1, Number(params.days ?? 14)))

  const timeseriesData = checkName
    ? await getMetricTimeseries(
        {
          check_name: checkName,
          customer_id: customerId || undefined,
          days,
        },
        token,
      ).catch(() => ({ items: [] }))
    : null

  return (
    <div className="space-y-6 p-6">
      <PageHeader
        title="Metrics"
        description="Workload trend per hari berdasarkan hasil pengecekan"
        actions={
          <div className="flex items-center gap-2">
            <CustomerSelector customers={customers} customerId={customerId} allowAll />
            <MetricFilters customerId={customerId} customerChecks={customerChecks} />
          </div>
        }
      />
      {timeseriesData ? (
        <MetricsCharts items={timeseriesData.items} />
      ) : (
        <EmptyState
          title="Select a check"
          description="Use the check filter above to view metric trends"
        />
      )}
    </div>
  )
}
