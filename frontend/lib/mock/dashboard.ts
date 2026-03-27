// Mock data for dashboard preview — remove when backend is fully connected
import type { DashboardSummary, CheckRunSummary, Finding, CheckResult, Customer } from '@/lib/types/api'
import type { ReportSchedule } from '@/lib/schedule-utils'

const now = new Date()
const h = (hours: number) => new Date(now.getTime() - hours * 3600 * 1000).toISOString()

export const MOCK_CUSTOMERS: Customer[] = [
  {
    id: 'cust-1',
    name: 'aryanoble',
    display_name: 'Arya Noble',
    checks: ['daily-arbel', 'daily-budget', 'backup'],
    slack_enabled: false,
    slack_channel: null,
    report_mode: 'summary',
    label: null,
    accounts: [
      { id: 'acc-1', profile_name: 'connect-prod', account_id: '620463044477', display_name: 'CONNECT Prod (Non CIS)', is_active: true, auth_method: 'profile', role_arn: null, external_id: null, aws_access_key_id: null, region: null, config_extra: {} },
      { id: 'acc-2', profile_name: 'cis-erha', account_id: '451916275465', display_name: 'CIS ERHA', is_active: true, auth_method: 'profile', role_arn: null, external_id: null, aws_access_key_id: null, region: null, config_extra: {} },
      { id: 'acc-3', profile_name: 'dermies-max', account_id: '637423567244', display_name: 'DERMIES MAX', is_active: true, auth_method: 'profile', role_arn: null, external_id: null, aws_access_key_id: null, region: null, config_extra: {} },
      { id: 'acc-4', profile_name: 'erha-buddy', account_id: '486250145105', display_name: 'ERHA BUDDY', is_active: true, auth_method: 'profile', role_arn: null, external_id: null, aws_access_key_id: null, region: null, config_extra: {} },
      { id: 'acc-5', profile_name: 'public-web', account_id: '211125667194', display_name: 'PUBLIC WEB', is_active: true, auth_method: 'profile', role_arn: null, external_id: null, aws_access_key_id: null, region: null, config_extra: {} },
      { id: 'acc-6', profile_name: 'dwh', account_id: '084056488725', display_name: 'DWH', is_active: true, auth_method: 'profile', role_arn: null, external_id: null, aws_access_key_id: null, region: null, config_extra: {} },
      { id: 'acc-7', profile_name: 'HRIS', account_id: '493314732063', display_name: 'HRIS', is_active: true, auth_method: 'profile', role_arn: null, external_id: null, aws_access_key_id: null, region: null, config_extra: {} },
      { id: 'acc-8', profile_name: 'sfa', account_id: '546158667544', display_name: 'SFA', is_active: true, auth_method: 'profile', role_arn: null, external_id: null, aws_access_key_id: null, region: null, config_extra: {} },
    ],
  },
  {
    id: 'cust-2',
    name: 'nabati',
    display_name: 'Nabati Group',
    checks: ['guardduty', 'cloudwatch_alarms', 'backup_status'],
    slack_enabled: false,
    slack_channel: null,
    report_mode: 'summary',
    label: null,
    accounts: [
      { id: 'acc-3', profile_name: 'nabati-prod', account_id: '345678901234', display_name: 'Nabati Production', is_active: true, auth_method: 'access_key', role_arn: null, external_id: null, aws_access_key_id: null, region: null, config_extra: {} },
    ],
  },
]

export const MOCK_SUMMARY: DashboardSummary = {
  customer_id: 'cust-1',
  window_hours: 24,
  generated_at: now.toISOString(),
  since: h(24),
  runs: {
    total: 14,
    single: 8,
    all: 4,
    arbel: 2,
    latest_created_at: h(1),
  },
  results: {
    total: 42,
    ok: 31,
    warn: 7,
    error: 4,
    alarm: 0,
    no_data: 0,
  },
  findings: {
    total: 9,
    by_severity: {
      CRITICAL: 1,
      HIGH: 3,
      MEDIUM: 4,
      LOW: 1,
    },
  },
  metrics: {
    total: 18,
    by_status: { ok: 12, warn: 4, error: 2 },
  },
  top_checks: [
    { check_name: 'daily-arbel', runs: 5 },
    { check_name: 'daily-budget', runs: 4 },
    { check_name: 'backup', runs: 3 },
    { check_name: 'alarm_verification', runs: 2 },
  ],
}

export const MOCK_HISTORY: CheckRunSummary[] = [
  {
    check_run_id: 'run-1',
    check_name: 'daily-arbel',
    check_mode: 'specific',
    created_at: h(1),
    execution_time_seconds: 8.4,
    slack_sent: false,
    results_summary: { total: 2, ok: 1, warn: 0, error: 1 },
  },
  {
    check_run_id: 'run-2',
    check_name: 'daily-budget',
    check_mode: 'specific',
    created_at: h(3),
    execution_time_seconds: 5.2,
    slack_sent: false,
    results_summary: { total: 2, ok: 1, warn: 1, error: 0 },
  },
  {
    check_run_id: 'run-3',
    check_name: 'all',
    check_mode: 'all',
    created_at: h(6),
    execution_time_seconds: 42.1,
    slack_sent: false,
    results_summary: { total: 8, ok: 6, warn: 1, error: 1 },
  },
  {
    check_run_id: 'run-4',
    check_name: 'backup',
    check_mode: 'specific',
    created_at: h(12),
    execution_time_seconds: 3.7,
    slack_sent: false,
    results_summary: { total: 2, ok: 2, warn: 0, error: 0 },
  },
  {
    check_run_id: 'run-5',
    check_name: 'alarm_verification',
    check_mode: 'specific',
    created_at: h(18),
    execution_time_seconds: 11.3,
    slack_sent: false,
    results_summary: { total: 2, ok: 1, warn: 1, error: 0 },
  },
]

export const MOCK_FINDINGS: Finding[] = [
  {
    id: 'f1',
    check_run_id: 'run-1',
    account: { id: 'acc-1', profile_name: 'connect-prod', display_name: 'CONNECT Prod (Non CIS)' },
    check_name: 'daily-arbel',
    finding_key: 'arbel-rds-001',
    severity: 'CRITICAL',
    title: 'RDS ACU Utilization > 75%',
    description: 'noncis-prod-rds ACU utilization has exceeded threshold. Immediate investigation required.',
    created_at: h(1),
  },
  {
    id: 'f2',
    check_run_id: 'run-1',
    account: { id: 'acc-2', profile_name: 'cis-erha', display_name: 'CIS ERHA' },
    check_name: 'daily-arbel',
    finding_key: 'arbel-mem-001',
    severity: 'HIGH',
    title: 'RDS FreeableMemory Below Threshold',
    description: 'cis-prod-rds writer instance has less than 20GB freeable memory.',
    created_at: h(2),
  },
  {
    id: 'f3',
    check_run_id: 'run-2',
    account: { id: 'acc-3', profile_name: 'dermies-max', display_name: 'DERMIES MAX' },
    check_name: 'daily-budget',
    finding_key: 'budget-001',
    severity: 'HIGH',
    title: 'Budget Threshold Exceeded',
    description: 'Monthly AWS spend has exceeded 80% of allocated budget.',
    created_at: h(3),
  },
  {
    id: 'f4',
    check_run_id: 'run-3',
    account: { id: 'acc-1', profile_name: 'connect-prod', display_name: 'CONNECT Prod (Non CIS)' },
    check_name: 'backup',
    finding_key: 'backup-001',
    severity: 'MEDIUM',
    title: 'Backup Job Failed',
    description: 'Scheduled backup job for RDS instance failed last night.',
    created_at: h(6),
  },
  {
    id: 'f5',
    check_run_id: 'run-3',
    account: { id: 'acc-7', profile_name: 'HRIS', display_name: 'HRIS' },
    check_name: 'backup',
    finding_key: 'backup-002',
    severity: 'MEDIUM',
    title: 'Backup Retention Policy Not Met',
    description: 'HRIS backup retention is below the required 30-day policy.',
    created_at: h(6),
  },
]

export const MOCK_RESULTS: CheckResult[] = [
  {
    customer_id: 'cust-1',
    account: { id: 'acc-1', profile_name: 'connect-prod', display_name: 'CONNECT Prod (Non CIS)' },
    check_name: 'daily-arbel',
    status: 'ERROR',
    summary: 'ACU utilization exceeded 75% threshold on noncis-prod-rds',
    output: '',
  },
  {
    customer_id: 'cust-1',
    account: { id: 'acc-2', profile_name: 'cis-erha', display_name: 'CIS ERHA' },
    check_name: 'daily-arbel',
    status: 'WARN',
    summary: 'FreeableMemory below threshold on cis-prod-rds writer',
    output: '',
  },
  {
    customer_id: 'cust-1',
    account: { id: 'acc-3', profile_name: 'dermies-max', display_name: 'DERMIES MAX' },
    check_name: 'daily-arbel',
    status: 'OK',
    summary: 'All RDS metrics within thresholds',
    output: '',
  },
  {
    customer_id: 'cust-1',
    account: { id: 'acc-4', profile_name: 'erha-buddy', display_name: 'ERHA BUDDY' },
    check_name: 'daily-arbel',
    status: 'WARN',
    summary: 'DatabaseConnections approaching limit (380/500)',
    output: '',
  },
]

export const MOCK_SCHEDULES: ReportSchedule[] = [
  {
    customerId: 'cust-1',
    customerName: 'Arya Noble',
    scheduleTimes: ['08:00', '19:00'],
    lastReportSentAt: h(14), // overdue — last sent 14h ago, next was 08:00 today
    lastCheckRunAt: h(1),
    reportSentWithLastRun: false,
  },
  {
    customerId: 'cust-2',
    customerName: 'Nabati Group',
    scheduleTimes: ['09:00'],
    lastReportSentAt: h(2),
    lastCheckRunAt: h(2),
    reportSentWithLastRun: true,
  },
]
