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
} from 'recharts'
import type { MetricTimeseriesItem } from '@/lib/api/metrics'

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

function formatDate(dateStr: string) {
  return new Date(dateStr).toLocaleDateString('en-GB', { day: '2-digit', month: 'short' })
}

function formatValue(value: number | null, unit?: string) {
  if (value === null || value === undefined) return '—'
  const rounded = Math.round(value * 100) / 100
  return unit ? `${rounded} ${unit}` : String(rounded)
}

// Detect unit from metric name
function inferUnit(metricName: string): string | undefined {
  if (metricName.includes('percent') || metricName.includes('utilization') || metricName.includes('ratio') || metricName.includes('free_percent')) return '%'
  if (metricName.includes('bytes')) return 'bytes'
  return undefined
}

interface MetricChartProps {
  metricName: string
  data: Record<string, unknown>[]
  accounts: string[]
}

function MetricChart({ metricName, data, accounts }: MetricChartProps) {
  const unit = inferUnit(metricName)
  const label = metricName.replace(/_/g, ' ')

  return (
    <div className="rounded-lg border border-border/40 bg-card p-4">
      <p className="mb-3 text-sm font-medium capitalize text-foreground">{label}</p>
      <ResponsiveContainer width="100%" height={180}>
        <LineChart data={data} margin={{ top: 4, right: 8, left: -16, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" opacity={0.4} />
          <XAxis
            dataKey="date"
            tickFormatter={formatDate}
            tick={{ fontSize: 11, fill: 'hsl(var(--muted-foreground))' }}
            tickLine={false}
          />
          <YAxis
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
            formatter={(value: number) => [formatValue(value, unit), '']}
            labelFormatter={formatDate}
          />
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
