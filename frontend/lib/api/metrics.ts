import { apiFetch, apiFetchText } from './client'
import type { PaginatedResponse, MetricSample, MetricStatus } from '@/lib/types/api'

export interface MetricTimeseriesItem {
  date: string
  metric_name: string
  account_id: string
  account_display_name: string
  avg_value: number | null
  max_value: number | null
  sample_count: number
}

export interface WorkloadMonthlyReport {
  customer_id: string
  month: string
  metric_fluctuations: Array<{
    metric_name: string
    sample_count: number
    days_with_samples: number
    avg_value: number
    min_value: number
    max_value: number
    daily_avg_range: number
  }>
  resource_fluctuations: Array<{
    account_display_name: string
    resource_id: string
    resource_name: string
    metric_name: string
    sample_count: number
    days_with_samples: number
    avg_value: number
    min_value: number
    max_value: number
    daily_avg_range: number
  }>
  stuck_summary: {
    threshold_days: number
    guardduty_active: number
    cloudwatch_active: number
    guardduty_stuck: number
    cloudwatch_stuck: number
    items: Array<{
      check_name: string
      account_display_name: string
      severity: string
      title: string
      age_days: number
      last_seen_at: string
    }>
  }
  cost_summary: {
    impacted_accounts: number
    accounts: Array<{
      account_display_name: string
      anomalies_today_peak: number
      anomalies_total_peak: number
    }>
  }
}

interface TimeseriesParams {
  check_name: string
  customer_id?: string
  account_id?: string
  days?: number
}

export async function getMetricTimeseries(
  params: TimeseriesParams,
  token: string,
): Promise<{ items: MetricTimeseriesItem[] }> {
  const query = new URLSearchParams()
  query.set('check_name', params.check_name)
  if (params.customer_id) query.set('customer_id', params.customer_id)
  if (params.account_id) query.set('account_id', params.account_id)
  if (params.days !== undefined) query.set('days', String(params.days))
  return apiFetch<{ items: MetricTimeseriesItem[] }>(`/metrics/timeseries?${query}`, { token })
}

interface WorkloadMonthlyParams {
  customer_id: string
  year?: number
  month?: number
  target_runs_per_day?: number
  stuck_days_threshold?: number
}

export async function getWorkloadMonthlyReport(
  params: WorkloadMonthlyParams,
  token: string,
): Promise<WorkloadMonthlyReport> {
  const query = new URLSearchParams()
  query.set('customer_id', params.customer_id)
  if (params.year !== undefined) query.set('year', String(params.year))
  if (params.month !== undefined) query.set('month', String(params.month))
  if (params.target_runs_per_day !== undefined) {
    query.set('target_runs_per_day', String(params.target_runs_per_day))
  }
  if (params.stuck_days_threshold !== undefined) {
    query.set('stuck_days_threshold', String(params.stuck_days_threshold))
  }
  return apiFetch<WorkloadMonthlyReport>(`/metrics/workload-monthly-report?${query}`, { token })
}

export async function getWorkloadMonthlyReportHtml(
  params: WorkloadMonthlyParams,
  token: string,
): Promise<string> {
  const query = new URLSearchParams()
  query.set('customer_id', params.customer_id)
  if (params.year !== undefined) query.set('year', String(params.year))
  if (params.month !== undefined) query.set('month', String(params.month))
  if (params.target_runs_per_day !== undefined) {
    query.set('target_runs_per_day', String(params.target_runs_per_day))
  }
  if (params.stuck_days_threshold !== undefined) {
    query.set('stuck_days_threshold', String(params.stuck_days_threshold))
  }
  return apiFetchText(`/metrics/workload-monthly-report/html?${query}`, { token })
}

export async function getWorkloadMonthlyReportCsv(
  params: WorkloadMonthlyParams,
  token: string,
): Promise<string> {
  const query = new URLSearchParams()
  query.set('customer_id', params.customer_id)
  if (params.year !== undefined) query.set('year', String(params.year))
  if (params.month !== undefined) query.set('month', String(params.month))
  if (params.target_runs_per_day !== undefined) {
    query.set('target_runs_per_day', String(params.target_runs_per_day))
  }
  if (params.stuck_days_threshold !== undefined) {
    query.set('stuck_days_threshold', String(params.stuck_days_threshold))
  }
  return apiFetchText(`/metrics/workload-monthly-report/csv?${query}`, { token })
}

interface MetricsParams {
  customer_id?: string
  check_name?: string
  metric_name?: string
  metric_status?: MetricStatus
  account_id?: string
  limit?: number
  offset?: number
}

export async function getMetrics(
  params: MetricsParams,
  token: string,
): Promise<PaginatedResponse<MetricSample>> {
  const query = new URLSearchParams()
  if (params.customer_id) query.set('customer_id', params.customer_id)
  if (params.check_name) query.set('check_name', params.check_name)
  if (params.metric_name) query.set('metric_name', params.metric_name)
  if (params.metric_status) query.set('metric_status', params.metric_status)
  if (params.account_id) query.set('account_id', params.account_id)
  if (params.limit !== undefined) query.set('limit', String(params.limit))
  if (params.offset !== undefined) query.set('offset', String(params.offset))
  return apiFetch<PaginatedResponse<MetricSample>>(`/metrics?${query}`, { token })
}
