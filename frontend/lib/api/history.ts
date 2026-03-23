import { apiFetch } from './client'
import type { PaginatedResponse, CheckRunSummary, CheckRunDetail } from '@/lib/types/api'

interface HistoryParams {
  customer_id?: string
  limit?: number
  offset?: number
}

export async function getHistory(
  params: HistoryParams,
  token: string,
): Promise<PaginatedResponse<CheckRunSummary>> {
  const query = new URLSearchParams()
  if (params.customer_id) query.set('customer_id', params.customer_id)
  if (params.limit !== undefined) query.set('limit', String(params.limit))
  if (params.offset !== undefined) query.set('offset', String(params.offset))
  return apiFetch<PaginatedResponse<CheckRunSummary>>(`/history?${query}`, { token })
}

export async function getRunDetail(runId: string, token: string): Promise<CheckRunDetail> {
  return apiFetch<CheckRunDetail>(`/history/${runId}`, { token })
}

export async function getRunReport(runId: string, token: string): Promise<string> {
  return apiFetch<string>(`/history/${runId}/report`, { token })
}
