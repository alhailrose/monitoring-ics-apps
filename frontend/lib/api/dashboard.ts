import { apiFetch } from './client'
import type { DashboardSummary } from '@/lib/types/api'

export interface CustomerOverviewItem {
  customer_id: string
  customer_name: string
  health: 'ok' | 'warn' | 'error'
  active_findings: number
  findings_by_severity: Record<string, number>
  results_24h: { ok: number; warn: number; error: number }
  last_run_at: string | null
}

export async function getCustomersOverview(token: string): Promise<CustomerOverviewItem[]> {
  const res = await apiFetch<{ items: CustomerOverviewItem[] }>('/dashboard/customers-overview', { token })
  return res.items
}

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
