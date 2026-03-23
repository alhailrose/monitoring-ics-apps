import { apiFetch } from './client'
import type { SessionsHealth, AwsProfile } from '@/lib/types/api'

interface SessionsHealthParams {
  customer_id?: string
  notify?: boolean
}

export async function getSessionsHealth(
  params: SessionsHealthParams,
  token: string,
): Promise<SessionsHealth> {
  const query = new URLSearchParams()
  if (params.customer_id) query.set('customer_id', params.customer_id)
  if (params.notify !== undefined) query.set('notify', String(params.notify))
  const qs = query.toString()
  return apiFetch<SessionsHealth>(`/sessions/health${qs ? `?${qs}` : ''}`, { token })
}

export async function getProfiles(token: string): Promise<{ profiles: AwsProfile[] }> {
  return apiFetch<{ profiles: AwsProfile[] }>('/profiles', { token })
}
