import Link from 'next/link'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { EmptyState } from '@/components/common/EmptyState'
import { StatusBadge } from '@/components/common/StatusBadge'
import type { CheckRunSummary } from '@/lib/types/api'

interface RecentHistoryProps {
  runs: CheckRunSummary[]
}

function formatDate(iso: string) {
  return new Date(iso).toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export function RecentHistory({ runs }: RecentHistoryProps) {
  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-medium">Recent History</CardTitle>
          <Link href="/history" className="text-xs text-muted-foreground hover:text-foreground transition-colors">
            View all →
          </Link>
        </div>
      </CardHeader>
      <CardContent>
        {runs.length === 0 ? (
          <EmptyState
            title="No runs yet"
            description="Execute a check to see history here"
          />
        ) : (
          <ul className="divide-y divide-border">
            {runs.map((run) => (
              <li key={run.check_run_id} className="flex items-center justify-between gap-4 py-3 text-sm">
                <div className="min-w-0 flex-1">
                  <p className="truncate font-medium text-foreground">
                    {run.check_name ?? run.check_mode}
                  </p>
                  <p className="text-xs text-muted-foreground mt-0.5">
                    {formatDate(run.created_at)}
                  </p>
                </div>
                <div className="flex shrink-0 items-center gap-2">
                  {run.results_summary.ok > 0 && (
                    <span className="flex items-center gap-1">
                      <StatusBadge status="OK" />
                      <span className="text-xs text-muted-foreground">{run.results_summary.ok}</span>
                    </span>
                  )}
                  {run.results_summary.warn > 0 && (
                    <span className="flex items-center gap-1">
                      <StatusBadge status="WARN" />
                      <span className="text-xs text-muted-foreground">{run.results_summary.warn}</span>
                    </span>
                  )}
                  {run.results_summary.error > 0 && (
                    <span className="flex items-center gap-1">
                      <StatusBadge status="ERROR" />
                      <span className="text-xs text-muted-foreground">{run.results_summary.error}</span>
                    </span>
                  )}
                </div>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  )
}
