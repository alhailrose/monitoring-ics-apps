import { apiRequest } from "./client"
import type { CheckMode, HistoryDetail, HistoryListResponse } from "../types/api"

type HistoryQueryOptions = {
  customerId: string
  startDate?: string
  endDate?: string
  checkMode?: CheckMode | ""
  checkName?: string
  limit?: number
  offset?: number
}

const toStartIso = (dateValue: string): string => {
  return new Date(`${dateValue}T00:00:00.000Z`).toISOString()
}

const toEndIso = (dateValue: string): string => {
  return new Date(`${dateValue}T23:59:59.999Z`).toISOString()
}

export const buildHistoryQuery = (options: HistoryQueryOptions): string => {
  const params = new URLSearchParams()

  params.set("customer_id", options.customerId)

  if (options.startDate) {
    params.set("start_date", toStartIso(options.startDate))
  }

  if (options.endDate) {
    params.set("end_date", toEndIso(options.endDate))
  }

  if (options.checkMode) {
    params.set("check_mode", options.checkMode)
  }

  if (options.checkName && options.checkName.trim().length > 0) {
    params.set("check_name", options.checkName.trim())
  }

  params.set("limit", String(options.limit ?? 50))
  params.set("offset", String(options.offset ?? 0))

  return params.toString()
}

export function listHistory(options: HistoryQueryOptions): Promise<HistoryListResponse> {
  const query = buildHistoryQuery(options)
  return apiRequest<HistoryListResponse>(`/history?${query}`)
}

export function getHistoryDetail(checkRunId: string): Promise<HistoryDetail> {
  return apiRequest<HistoryDetail>(`/history/${checkRunId}`)
}

export function getHistoryReport(checkRunId: string): Promise<{ report: string }> {
  return apiRequest<{ report: string }>(`/history/${checkRunId}/report`)
}
