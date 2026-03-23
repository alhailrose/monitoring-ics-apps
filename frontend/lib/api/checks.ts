import { apiFetch } from '@/lib/api/client'
import type { ExecuteResponse } from '@/lib/types/api'

interface ExecutePayload {
  customer_ids: string[]
  mode: string
  check_name?: string
  account_ids?: string[]
  send_slack: boolean
  check_params?: Record<string, unknown>
}

export async function executeChecks(
  payload: ExecutePayload,
  token: string,
): Promise<ExecuteResponse> {
  return apiFetch<ExecuteResponse>('/checks/execute', {
    method: 'POST',
    body: JSON.stringify(payload),
    token,
  })
}
