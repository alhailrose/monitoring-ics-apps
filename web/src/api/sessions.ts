import { apiRequest } from "./client"
import type { SessionHealthReport } from "../types/api"

type SessionHealthOptions = {
  customerId?: string
  notify?: boolean
}

export function checkSessionHealth(
  options: SessionHealthOptions = {},
): Promise<SessionHealthReport> {
  const params = new URLSearchParams()
  if (options.customerId) {
    params.set("customer_id", options.customerId)
  }
  if (options.notify) {
    params.set("notify", "true")
  }
  const query = params.toString()
  return apiRequest<SessionHealthReport>(`/sessions/health${query ? `?${query}` : ""}`)
}
