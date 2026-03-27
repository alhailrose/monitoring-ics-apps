import Link from 'next/link'
import { cn, formatDate } from '@/lib/utils'
import type { CustomerOverviewItem } from '@/lib/api/dashboard'

const SEVERITY_ORDER = ['CRITICAL', 'ALARM', 'HIGH', 'MEDIUM', 'LOW', 'INFO'] as const

const HEALTH_STYLES: Record<string, string> = {
  ok:    'border-emerald-500/30 bg-emerald-500/5',
  warn:  'border-yellow-500/30 bg-yellow-500/5',
  error: 'border-red-500/30 bg-red-500/5',
}

const HEALTH_DOT: Record<string, string> = {
  ok:    'bg-emerald-400',
  warn:  'bg-yellow-400',
  error: 'bg-red-400',
}

const HEALTH_LABEL: Record<string, string> = {
  ok:    'Healthy',
  warn:  'Warning',
  error: 'Critical',
}

const SEVERITY_COLORS: Record<string, string> = {
  CRITICAL: 'text-red-500',
  ALARM:    'text-red-400',
  HIGH:     'text-orange-400',
  MEDIUM:   'text-yellow-400',
  LOW:      'text-blue-400',
  INFO:     'text-slate-400',
}

interface Props {
  items: CustomerOverviewItem[]
}

export function CustomersOverviewGrid({ items }: Props) {
  if (items.length === 0) {
    return (
      <p className="py-12 text-center text-sm text-muted-foreground">
        No customers configured yet
      </p>
    )
  }

  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
      {items.map((item) => (
        <Link
          key={item.customer_id}
          href={`/dashboard?customer_id=${item.customer_id}`}
          className={cn(
            'group relative rounded-xl border p-4 transition-all hover:shadow-md hover:border-opacity-60',
            HEALTH_STYLES[item.health] ?? HEALTH_STYLES.ok,
          )}
        >
          {/* Header */}
          <div className="flex items-start justify-between gap-2 mb-3">
            <div className="min-w-0">
              <p className="font-semibold text-sm text-foreground truncate">{item.customer_name}</p>
              <div className="flex items-center gap-1.5 mt-0.5">
                <span className={cn('inline-block size-2 rounded-full shrink-0', HEALTH_DOT[item.health])} />
                <span className="text-xs text-muted-foreground">{HEALTH_LABEL[item.health]}</span>
              </div>
            </div>
          </div>

          {/* Active findings */}
          {item.active_findings > 0 ? (
            <div className="mb-3">
              <p className="text-xs text-muted-foreground mb-1">Active findings</p>
              <div className="flex flex-wrap gap-1.5">
                {SEVERITY_ORDER.filter((s) => item.findings_by_severity[s] > 0).map((s) => (
                  <span key={s} className={cn('text-xs font-medium', SEVERITY_COLORS[s])}>
                    {item.findings_by_severity[s]} {s}
                  </span>
                ))}
              </div>
            </div>
          ) : (
            <p className="text-xs text-muted-foreground mb-3">No active findings</p>
          )}

          {/* Last 24h results */}
          {(item.results_24h.ok + item.results_24h.warn + item.results_24h.error) > 0 && (
            <div className="flex gap-3 text-xs mb-3">
              {item.results_24h.ok > 0 && (
                <span className="text-emerald-400">{item.results_24h.ok} OK</span>
              )}
              {item.results_24h.warn > 0 && (
                <span className="text-yellow-400">{item.results_24h.warn} WARN</span>
              )}
              {item.results_24h.error > 0 && (
                <span className="text-red-400">{item.results_24h.error} ERR</span>
              )}
            </div>
          )}

          {/* Last run */}
          <p className="text-[11px] text-muted-foreground/70">
            {item.last_run_at ? `Last run ${formatDate(item.last_run_at)}` : 'No runs yet'}
          </p>
        </Link>
      ))}
    </div>
  )
}
