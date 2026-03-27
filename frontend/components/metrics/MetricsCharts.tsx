'use client'

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ReferenceLine,
} from 'recharts'
import type { MetricTimeseriesItem } from '@/lib/api/metrics'
import { formatDateShort } from '@/lib/utils'

const LINE_COLORS = [
  '#60a5fa', // blue-400
  '#34d399', // emerald-400
  '#f59e0b', // amber-400
  '#f87171', // red-400
  '#a78bfa', // violet-400
  '#38bdf8', // sky-400
  '#fb923c', // orange-400
  '#4ade80', // green-400
]

// Friendly label map for common metric names
const METRIC_LABELS: Record<string, string> = {
  cpu_utilization_percent:      'CPU Utilization (%)',
  memory_utilization_percent:   'Memory Utilization (%)',
  disk_utilization_percent:     'Disk Utilization (%)',
  network_utilization_percent:  'Network Utilization (%)',
  free_storage_bytes:           'Free Storage',
  free_memory_bytes:            'Free Memory',
  used_storage_bytes:           'Used Storage',
  used_memory_bytes:            'Used Memory',
  network_in_bytes:             'Network In',
  network_out_bytes:            'Network Out',
  network_receive_bytes_per_s:  'Network Receive (Avg)',
  network_transmit_bytes_per_s: 'Network Transmit (Avg)',
  iops_read:                    'IOPS Read',
  iops_write:                   'IOPS Write',
  cpu_credit_usage:             'CPU Credit Usage',
  cpu_credit_balance:           'CPU Credit Balance',
  db_connections:               'DB Connections',
  read_latency_ms:              'Read Latency (ms)',
  write_latency_ms:             'Write Latency (ms)',
  cost_anomaly_amount:          'Cost Anomaly (USD)',
  alarm_count:                  'Active Alarms',
  finding_count:                'Findings',
  notification_count:           'Notifications',
  backup_job_count:             'Backup Jobs',
}

function getMetricLabel(name: string): string {
  if (METRIC_LABELS[name]) return METRIC_LABELS[name]
  // Fallback: replace underscores, title-case
  return name
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase())
}

type MetricType = 'percent' | 'bytes' | 'ms' | 'usd' | 'count'

function inferMetricType(name: string): MetricType {
  if (name.includes('percent') || name.includes('utilization') || name.includes('ratio')) return 'percent'
  if (name.includes('bytes') || name.includes('network_in') || name.includes('network_out') ||
      name.includes('network_receive') || name.includes('network_transmit')) return 'bytes'
  if (name.includes('latency_ms') || name.includes('_ms')) return 'ms'
  if (name.includes('cost') || name.includes('amount') || name.includes('usd')) return 'usd'
  return 'count'
}

function formatBytes(bytes: number): string {
  if (bytes >= 1_073_741_824) return `${(bytes / 1_073_741_824).toFixed(2)} GB`
  if (bytes >= 1_048_576)     return `${(bytes / 1_048_576).toFixed(2)} MB`
  if (bytes >= 1_024)         return `${(bytes / 1_024).toFixed(2)} KB`
  return `${bytes} B`
}

function formatValue(value: number | null, type: MetricType): string {
  if (value === null || value === undefined) return '—'
  const rounded = Math.round(value * 100) / 100
  switch (type) {
    case 'percent': return `${rounded}%`
    case 'bytes':   return formatBytes(rounded)
    case 'ms':      return `${rounded} ms`
    case 'usd':     return `$${rounded}`
    default:        return String(rounded)
  }
}

function yTickFormatter(type: MetricType) {
  return (value: number) => {
    if (type === 'percent') return `${value}%`
    if (type === 'bytes')   return formatBytes(value)
    if (type === 'ms')      return `${value}ms`
    if (type === 'usd')     return `$${value}`
    return String(value)
  }
}

interface MetricChartProps {
  metricName: string
  data: Record<string, unknown>[]
  accounts: string[]
}

function MetricChart({ metricName, data, accounts }: MetricChartProps) {
  const type = inferMetricType(metricName)
  const label = getMetricLabel(metricName)
  const isPercent = type === 'percent'

  return (
    <div className="rounded-lg border border-border/40 bg-card p-4">
      <p className="mb-3 text-sm font-medium text-foreground">{label}</p>
      <ResponsiveContainer width="100%" height={180}>
        <LineChart data={data} margin={{ top: 4, right: 8, left: -16, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" opacity={0.4} />
          <XAxis
            dataKey="date"
            tickFormatter={formatDateShort}
            tick={{ fontSize: 11, fill: 'hsl(var(--muted-foreground))' }}
            tickLine={false}
          />
          <YAxis
            domain={isPercent ? [0, 100] : ['auto', 'auto']}
            tickFormatter={yTickFormatter(type)}
            tick={{ fontSize: 11, fill: 'hsl(var(--muted-foreground))' }}
            tickLine={false}
            axisLine={false}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: 'hsl(var(--card))',
              border: '1px solid hsl(var(--border))',
              borderRadius: '6px',
              fontSize: 12,
            }}
            formatter={(value: number) => [formatValue(value, type), '']}
            labelFormatter={formatDateShort}
          />
          {isPercent && (
            <ReferenceLine
              y={80}
              stroke="hsl(var(--destructive))"
              strokeDasharray="4 3"
              strokeWidth={1}
              opacity={0.5}
            />
          )}
          {accounts.length > 1 && (
            <Legend
              wrapperStyle={{ fontSize: 11, paddingTop: 8 }}
              formatter={(v) => <span style={{ color: 'hsl(var(--muted-foreground))' }}>{v}</span>}
            />
          )}
          {accounts.map((account, i) => (
            <Line
              key={account}
              type="monotone"
              dataKey={account}
              stroke={LINE_COLORS[i % LINE_COLORS.length]}
              strokeWidth={2}
              dot={{ r: 3 }}
              activeDot={{ r: 5 }}
              connectNulls
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}

interface MetricsChartsProps {
  items: MetricTimeseriesItem[]
}

export function MetricsCharts({ items }: MetricsChartsProps) {
  if (items.length === 0) {
    return (
      <p className="py-8 text-center text-sm text-muted-foreground">
        No metric data yet — run a check to collect data
      </p>
    )
  }

  // Group by metric_name
  const metricNames = [...new Set(items.map((i) => i.metric_name))]
  const accounts = [...new Set(items.map((i) => i.account_display_name))]

  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3">
      {metricNames.map((metricName) => {
        // Pivot: [{date, account1: value, account2: value, ...}]
        const byDate: Record<string, Record<string, unknown>> = {}
        for (const item of items.filter((i) => i.metric_name === metricName)) {
          if (!byDate[item.date]) byDate[item.date] = { date: item.date }
          byDate[item.date][item.account_display_name] = item.avg_value
        }
        const chartData = Object.values(byDate).sort((a, b) =>
          String(a.date).localeCompare(String(b.date))
        )

        return (
          <MetricChart
            key={metricName}
            metricName={metricName}
            data={chartData}
            accounts={accounts}
          />
        )
      })}
    </div>
  )
}
