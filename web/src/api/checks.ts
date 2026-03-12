import { apiRequest } from "./client"
import type { AvailableCheck, ExecuteCheckRequest, ExecuteCheckResponse } from "../types/api"
import { normalizeExecuteResponse } from "../features/checks/normalize-execute-response"

export async function listAvailableChecks(): Promise<AvailableCheck[]> {
  const data = await apiRequest<{ checks: AvailableCheck[] }>("/checks/available")
  return data.checks
}

export async function executeChecks(payload: ExecuteCheckRequest): Promise<ExecuteCheckResponse> {
  const data = await apiRequest<ExecuteCheckResponse & { consolidated_output?: string }>(
    "/checks/execute",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    },
  )

  return normalizeExecuteResponse(data)
}
