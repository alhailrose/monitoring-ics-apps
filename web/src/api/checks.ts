import { apiRequest } from "./client"
import type { AvailableCheck, ExecuteCheckRequest, ExecuteCheckResponse } from "../types/api"

export async function listAvailableChecks(): Promise<AvailableCheck[]> {
  const data = await apiRequest<{ checks: AvailableCheck[] }>("/checks/available")
  return data.checks
}

export function executeChecks(payload: ExecuteCheckRequest): Promise<ExecuteCheckResponse> {
  return apiRequest<ExecuteCheckResponse>("/checks/execute", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  })
}
