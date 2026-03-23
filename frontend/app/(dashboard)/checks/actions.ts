'use server'

import { getToken } from '@/lib/server-token'
import { executeChecks } from '@/lib/api/checks'
import type { ExecuteResponse } from '@/lib/types/api'

export async function runChecks(formData: FormData): Promise<{ data?: ExecuteResponse; error?: string }> {
  try {
    const token = await getToken()
    const mode = formData.get('mode') as string
    const customerIds = formData.getAll('customer_ids') as string[]
    const sendSlack = formData.get('send_slack') === 'true'

    const payload: Parameters<typeof executeChecks>[0] = {
      customer_ids: customerIds.filter(Boolean),
      mode,
      send_slack: sendSlack,
    }

    if (mode === 'single') {
      payload.check_name = formData.get('check_name') as string
      payload.account_ids = formData.getAll('account_ids') as string[]
    }

    // Pass check_params (e.g. window_hours for utilization checks)
    const checkParamsRaw = formData.get('check_params') as string | null
    if (checkParamsRaw) {
      try {
        payload.check_params = JSON.parse(checkParamsRaw)
      } catch {
        // ignore malformed check_params
      }
    }

    const data = await executeChecks(payload, token)
    return { data }
  } catch (err) {
    return { error: err instanceof Error ? err.message : 'Unknown error' }
  }
}
