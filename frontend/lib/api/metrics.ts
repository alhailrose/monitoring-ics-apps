import { apiFetch } from './client'
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
