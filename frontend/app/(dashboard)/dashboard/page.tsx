// Server Component — fetches all dashboard data server-side
import { getToken } from '@/lib/server-token'
import { getCustomers } from '@/lib/api/customers'
import { getDashboardSummary } from '@/lib/api/dashboard'
import { getHistory, getRunDetail } from '@/lib/api/history'
import { getFindings } from '@/lib/api/findings'
import { PageHeader } from '@/components/common/PageHeader'
import { CustomerSelector } from '@/components/common/CustomerSelector'
import { WindowSelector } from '@/components/common/WindowSelector'
import { StatCards } from '@/components/dashboard/StatCards'
import { RecentHistory } from '@/components/dashboard/RecentHistory'
import { AccountOverview } from '@/components/dashboard/AccountOverview'
import type { ReportSchedule } from '@/lib/schedule-utils'

interface PageProps {
  searchParams: Promise<{ customer_id?: string; window_hours?: string }>
}

export default async function DashboardPage({ searchParams }: PageProps) {
  const token = await getToken()
  const { customer_id, window_hours } = await searchParams

  const customers = await getCustomers(token).catch(() => [])
  const customerId = customer_id ?? customers[0]?.id ?? ''
  const windowHours = Math.min(Math.max(Number(window_hours ?? 24), 1), 720)

  const [summary, historyData, findingsData] = await Promise.all([
    customerId ? getDashboardSummary(customerId, windowHours, token).catch(() => null) : Promise.resolve(null),
    customerId ? getHistory({ customer_id: customerId, limit: 5 }, token).catch(() => null) : Promise.resolve(null),
    customerId ? getFindings({ customer_id: customerId, limit: 100 }, token).catch(() => null) : Promise.resolve(null),
  ])

  const latestRun = historyData?.items?.[0] ?? null
  const latestRunDetail = latestRun
    ? await getRunDetail(latestRun.check_run_id, token).catch(() => null)
    : null

  // Build report schedules from customer data (no backend endpoint yet — derived client-side)
  const reportSchedules: ReportSchedule[] = customers.map((c) => ({
    customerId: c.id,
    customerName: c.display_name,
    scheduleTimes: ['08:00', '19:00'],
    lastReportSentAt: null,
    lastCheckRunAt: historyData?.items?.[0]?.created_at ?? null,
    reportSentWithLastRun: false,
  }))

  return (
    <div className="space-y-6 p-6 max-w-full">
      <PageHeader
        title="Dashboard"
        description="Overview of your cloud monitoring activity"
        actions={
          customers.length > 0 ? (
            <div className="flex items-center gap-2">
              <WindowSelector windowHours={windowHours} />
              <CustomerSelector customers={customers} customerId={customerId} />
            </div>
          ) : undefined
        }
      />

      <StatCards
        summary={summary}
        reportSchedules={[]}
        currentCustomerId={customerId}
      />

      <div className="grid gap-6 lg:grid-cols-[1fr_340px]">
        <AccountOverview
          findings={findingsData?.items ?? []}
          results={latestRunDetail?.results ?? []}
          runName={latestRun?.check_name ?? latestRun?.check_mode}
        />
        <RecentHistory runs={historyData?.items ?? []} />
      </div>
    </div>
  )
}
