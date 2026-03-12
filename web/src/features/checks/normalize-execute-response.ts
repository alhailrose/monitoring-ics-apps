import type { ExecuteCheckResponse } from "../../types/api"

type ExecuteResponseWire = Partial<ExecuteCheckResponse> & {
  consolidated_output?: string
}

export const normalizeExecuteResponse = (payload: ExecuteResponseWire): ExecuteCheckResponse => {
  const consolidated_outputs =
    payload.consolidated_outputs && typeof payload.consolidated_outputs === "object"
      ? payload.consolidated_outputs
      : payload.consolidated_output
        ? { default: payload.consolidated_output }
        : {}

  return {
    check_runs: Array.isArray(payload.check_runs) ? payload.check_runs : [],
    execution_time_seconds:
      typeof payload.execution_time_seconds === "number" ? payload.execution_time_seconds : 0,
    results: Array.isArray(payload.results) ? payload.results : [],
    consolidated_outputs,
  }
}
