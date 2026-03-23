import { apiFetch } from './client'
import type { PaginatedResponse, Finding, FindingSeverity } from '@/lib/types/api'

interface FindingsParams {
  customer_id?: string
  check_name?: string
  severity?: FindingSeverity
  account_id?: string
  limit?: number
  offset?: number
}

export async function getFindings(
  params: FindingsParams,
  token: string,
): Promise<PaginatedResponse<Finding>> {
  const query = new URLSearchParams()
  if (params.customer_id) query.set('customer_id', params.customer_id)
  if (params.check_name) query.set('check_name', params.check_name)
  if (params.severity) query.set('severity', params.severity)
  if (params.account_id) query.set('account_id', params.account_id)
  if (params.limit !== undefined) query.set('limit', String(params.limit))
  if (params.offset !== undefined) query.set('offset', String(params.offset))
  return apiFetch<PaginatedResponse<Finding>>(`/findings?${query}`, { token })
}
