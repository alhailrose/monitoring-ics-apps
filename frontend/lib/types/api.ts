// ─── Auth ────────────────────────────────────────────────────────────────────

export type UserRole = 'super_user' | 'user'

export interface User {
  id: string
  username: string
  role: UserRole
}

export interface TokenResponse {
  access_token: string
  token_type: 'bearer'
  expires_at: string
}

export interface SessionPayload {
  sub: string
  username: string
  role: UserRole
  exp: number
}

// ─── Customers & Accounts ────────────────────────────────────────────────────

export type AwsAuthMode = 'assume_role' | 'sso' | 'aws_login' | 'access_key'

export interface Account {
  id: string
  profile_name: string
  account_id: string
  display_name: string
  is_active: boolean
  aws_auth_mode: AwsAuthMode
  role_arn: string | null
  external_id: string | null
  config_extra: Record<string, unknown>
  alarm_names?: string[] | null
}

export type ReportMode = 'summary' | 'detailed'

export interface Customer {
  id: string
  name: string
  display_name: string
  checks: string[]
  slack_enabled: boolean
  slack_channel: string | null
  report_mode: ReportMode
  label: string | null
  accounts: Account[]
}

// ─── Runs & Results ──────────────────────────────────────────────────────────

export type CheckStatus = 'OK' | 'WARN' | 'ERROR' | 'ALARM' | 'NO_DATA'

export type ErrorClass =
  | 'sso_expired'
  | 'assume_role_failed'
  | 'invalid_credentials'
  | 'no_config'
  | null

export interface CheckResultAccount {
  id: string
  profile_name: string
  display_name: string
}

export interface CheckResult {
  customer_id: string
  account: CheckResultAccount
  check_name: string
  status: CheckStatus
  summary: string
  output: string
  details?: Record<string, unknown> | null
  error_class?: ErrorClass
}

export interface CheckRunSummary {
  check_run_id: string
  check_mode: string
  check_name: string
  created_at: string
  execution_time_seconds: number
  slack_sent: boolean
  results_summary: {
    total: number
    ok: number
    warn: number
    error: number
  }
}

export interface CheckRunDetailCustomer {
  id: string
  name: string
  display_name: string
}

export interface CheckRunDetail extends CheckRunSummary {
  customer: CheckRunDetailCustomer
  results: CheckResult[]
}

export interface PaginatedResponse<T> {
  total: number
  items: T[]
}

// ─── Findings ────────────────────────────────────────────────────────────────

export type FindingSeverity =
  | 'CRITICAL'
  | 'HIGH'
  | 'MEDIUM'
  | 'LOW'
  | 'INFO'
  | 'ALARM'

export interface Finding {
  id: string
  check_run_id: string
  customer: { id: string; display_name: string }
  account: CheckResultAccount
  check_name: string
  finding_key: string
  severity: FindingSeverity
  title: string
  description: string
  created_at: string
}

// ─── Metrics ─────────────────────────────────────────────────────────────────

export type MetricStatus = 'ok' | 'warn' | 'error'

export interface MetricSample {
  id: string
  check_run_id: string
  customer: { id: string; display_name: string }
  account: CheckResultAccount
  check_name: string
  metric_name: string
  metric_status: MetricStatus
  value_num: number
  unit: string
  resource_role: string
  resource_id: string
  resource_name: string
  service_type: string
  section_name: string
  created_at: string
}

// ─── Dashboard ───────────────────────────────────────────────────────────────

export interface DashboardSummary {
  customer_id: string
  window_hours: number
  generated_at: string
  since: string
  runs: {
    total: number
    single: number
    all: number
    arbel: number
    latest_created_at: string | null
  }
  results: {
    total: number
    ok: number
    warn: number
    error: number
    alarm: number
    no_data: number
  }
  findings: {
    total: number
    by_severity: Partial<Record<FindingSeverity, number>>
  }
  metrics: {
    total: number
    by_status: Partial<Record<MetricStatus, number>>
  }
  top_checks: Array<{ check_name: string; runs: number }>
}

// ─── Check Execution ─────────────────────────────────────────────────────────

export interface ExecuteResponse {
  check_runs: Array<{
    customer_id: string
    check_run_id: string
    slack_sent: boolean
  }>
  execution_time_seconds: number
  results: CheckResult[]
  consolidated_outputs: Record<string, string>
  backup_overviews: Record<string, unknown>
}

// ─── Sessions & Profiles ─────────────────────────────────────────────────────

export type SessionStatus = 'ok' | 'expired' | 'no_config' | 'error'

export interface ProfileHealth {
  profile_name: string
  account_id: string
  display_name: string
  status: SessionStatus
  error: string
  sso_session: string | null
  login_command: string
}

export interface SessionsHealth {
  total_profiles: number
  ok: number
  expired: number
  error: number
  profiles: ProfileHealth[]
  sso_sessions: Record<
    string,
    {
      session_name: string
      login_command: string
      status: SessionStatus
      profiles_ok: string[]
      profiles_expired: string[]
      profiles_error: string[]
    }
  >
}

export interface AwsProfile {
  profile_name: string
  sso_session: string | null
  region: string
}
