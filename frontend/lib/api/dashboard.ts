import { apiFetch } from './client'
import type { DashboardSummary } from '@/lib/types/api'

export async function getDashboardSummary(
  customerId: string,
  windowHours: number,
  token: string,
): Promise<DashboardSummary> {
  const query = new URLSearchParams({
    customer_id: customerId,
    window_hours: String(windowHours),
  })
  return apiFetch<DashboardSummary>(`/dashboard/summary?${query}`, { token })
}
