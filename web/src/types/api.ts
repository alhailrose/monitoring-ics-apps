export type CheckMode = "single" | "all" | "arbel"

export type CheckStatus = "OK" | "WARN" | "ERROR" | "ALARM" | "NO_DATA"

export type Account = {
  id: string
  profile_name: string
  account_id: string | null
  display_name: string
  is_active: boolean
  config_extra: Record<string, unknown> | null
  region: string | null
  alarm_names: string[] | null
  created_at: string
}

export type Customer = {
  id: string
  name: string
  display_name: string
  checks: string[]
  sso_session: string | null
  slack_webhook_url: string | null
  slack_channel: string | null
  slack_enabled: boolean
  created_at: string
  updated_at: string
  accounts: Account[]
}

export type AvailableCheck = {
  name: string
  class: string
}

export type CheckResultItem = {
  account: {
    id: string
    profile_name: string
    display_name: string
  }
  check_name: string
  status: CheckStatus
  summary: string
  output: string
}

export type ExecuteCheckRequest = {
  customer_id: string
  mode: CheckMode
  check_name?: string
  account_ids?: string[] | null
  send_slack: boolean
  check_params?: Record<string, unknown> | null
}

export type ExecuteCheckResponse = {
  check_run_id: string
  execution_time_seconds: number
  results: CheckResultItem[]
  consolidated_output: string
  slack_sent: boolean
}

export type HistorySummary = {
  check_run_id: string
  check_mode: CheckMode
  check_name: string | null
  created_at: string
  execution_time_seconds: number | null
  slack_sent: boolean
  results_summary: {
    total: number
    ok: number
    warn: number
    error: number
  }
}

export type HistoryListResponse = {
  total: number
  items: HistorySummary[]
}

export type HistoryDetail = {
  check_run_id: string
  customer: {
    id: string
    name: string
    display_name: string
  }
  check_mode: CheckMode
  check_name: string | null
  created_at: string
  execution_time_seconds: number | null
  slack_sent: boolean
  results: Array<{
    account: {
      id: string
      profile_name: string
      display_name: string
    }
    check_name: string
    status: CheckStatus
    summary: string
    output: string
    details: Record<string, unknown> | null
    created_at: string
  }>
}

export type ProfileDetectionResponse = {
  all_profiles: string[]
  mapped_profiles: string[]
  unmapped_profiles: string[]
}

export type CreateCustomerRequest = {
  name: string
  display_name: string
  checks?: string[]
  slack_webhook_url?: string | null
  slack_channel?: string | null
  slack_enabled?: boolean
  sso_session?: string | null
}

export type UpdateCustomerRequest = Partial<
  Pick<
    CreateCustomerRequest,
    "display_name" | "checks" | "slack_webhook_url" | "slack_channel" | "slack_enabled"
  >
>

export type CreateAccountRequest = {
  profile_name: string
  display_name: string
  config_extra?: Record<string, unknown> | null
  region?: string | null
  alarm_names?: string[] | null
}

export type UpdateAccountRequest = {
  display_name?: string
  is_active?: boolean
  config_extra?: Record<string, unknown> | null
  region?: string | null
  alarm_names?: string[] | null
}

export type ProfileStatus = {
  profile_name: string
  account_id: string | null
  display_name: string
  status: "ok" | "expired" | "error" | "no_config" | "unknown"
  error: string
  sso_session: string
  login_command: string
}

export type SsoSessionInfo = {
  session_name: string
  login_command: string
  status: "ok" | "expired" | "error"
  profiles_ok: string[]
  profiles_expired: string[]
  profiles_error: string[]
}

export type SessionHealthReport = {
  total_profiles: number
  ok: number
  expired: number
  error: number
  profiles: ProfileStatus[]
  sso_sessions: Record<string, SsoSessionInfo>
}
