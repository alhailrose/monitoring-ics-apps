import { getToken } from '@/lib/server-token'
import { getCustomers } from '@/lib/api/customers'
import {
  getWorkloadMonthlyReport,
} from '@/lib/api/metrics'
import { PageHeader } from '@/components/common/PageHeader'
import { CustomerSelector } from '@/components/common/CustomerSelector'
import { EmptyState } from '@/components/common/EmptyState'

interface SearchParams {
  customer_id?: string
  year?: string
  month?: string
}

export default async function ReportsPage({
  searchParams,
}: {
  searchParams: Promise<SearchParams>
}) {
  const params = await searchParams
  const token = await getToken()

  const customers = await getCustomers(token).catch(() => [])
  const customerId = params.customer_id ?? ''

  const now = new Date()
  const year = Number(params.year ?? now.getFullYear())
  const month = Number(params.month ?? now.getMonth() + 1)

  const report = customerId
    ? await getWorkloadMonthlyReport(
        {
          customer_id: customerId,
          year,
          month,
          target_runs_per_day: 2,
          stuck_days_threshold: 7,
        },
        token,
      ).catch(() => null)
    : null

  const reportQuery = new URLSearchParams({
    customer_id: customerId,
    year: String(year),
    month: String(month),
    target_runs_per_day: '2',
    stuck_days_threshold: '7',
  }).toString()

  return (
    <div className="space-y-6 p-6">
      <PageHeader
        title="Reports"
        description="Customer monthly report (workload, stuck issues, and cost anomaly)"
        actions={
          <div className="flex items-center gap-2">
            <CustomerSelector customers={customers} customerId={customerId} allowAll />
          </div>
        }
      />

      {!customerId ? (
        <EmptyState
          title="Pilih customer"
          description="Pilih customer untuk melihat monthly report"
        />
      ) : !report ? (
        <EmptyState
          title="Report belum tersedia"
          description="Belum ada data report untuk customer/periode ini"
        />
      ) : (
        <div className="space-y-4">
          <div className="rounded-lg border border-border/40 bg-card p-4">
            <p className="text-sm font-medium text-foreground">Executive Summary {report.month}</p>
            <p className="text-xs text-muted-foreground mt-1">
              Fluktuasi metric: {report.metric_fluctuations.length} metric, resource fluktuatif: {report.resource_fluctuations.length} resource
            </p>
            <p className="text-xs text-muted-foreground mt-1">
              GuardDuty aktif/stuck: {report.stuck_summary.guardduty_active}/{report.stuck_summary.guardduty_stuck} · CloudWatch aktif/stuck: {report.stuck_summary.cloudwatch_active}/{report.stuck_summary.cloudwatch_stuck}
            </p>
            <p className="text-xs text-muted-foreground mt-1">
              Cost anomaly impacted accounts: {report.cost_summary.impacted_accounts}
            </p>

            <div className="flex flex-wrap items-center gap-2 mt-3">
              <a
                href={`/api/reports/workload-monthly-report/html?${reportQuery}`}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center rounded-md border border-border px-2.5 py-1.5 text-xs hover:bg-muted/40"
              >
                Preview HTML
              </a>
              <a
                href={`/api/reports/workload-monthly-report/csv?${reportQuery}`}
                className="inline-flex items-center rounded-md border border-border px-2.5 py-1.5 text-xs hover:bg-muted/40"
              >
                Download CSV
              </a>
            </div>
          </div>

          {report.stuck_summary.items.length > 0 && (
            <div className="rounded-lg border border-border/40 bg-card p-4">
              <p className="text-sm font-medium">Stuck Issues (Top)</p>
              <ul className="mt-2 space-y-1 text-xs text-muted-foreground">
                {report.stuck_summary.items.slice(0, 5).map((item, idx) => (
                  <li key={`${item.check_name}-${item.account_display_name}-${idx}`}>
                    • [{item.check_name}] {item.account_display_name}: {item.title} ({item.age_days} hari)
                  </li>
                ))}
              </ul>
            </div>
          )}

          {report.cost_summary.accounts.length > 0 && (
            <div className="rounded-lg border border-border/40 bg-card p-4">
              <p className="text-sm font-medium">Cost Anomaly Highlights</p>
              <ul className="mt-2 space-y-1 text-xs text-muted-foreground">
                {report.cost_summary.accounts.slice(0, 5).map((item, idx) => (
                  <li key={`${item.account_display_name}-${idx}`}>
                    • {item.account_display_name}: peak today {item.anomalies_today_peak}, peak total {item.anomalies_total_peak}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
