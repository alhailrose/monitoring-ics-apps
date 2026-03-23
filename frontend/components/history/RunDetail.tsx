'use client'

import { CustomerResultCard } from '@/components/checks/CustomerResultCard'
import { formatDate } from '@/lib/utils'
import type { CheckRunDetail as CheckRunDetailType } from '@/lib/types/api'

interface RunDetailProps {
  run: CheckRunDetailType
}

export function RunDetail({ run }: RunDetailProps) {
  const customerLabel = run.customer?.display_name ?? run.check_name ?? 'Unknown'

  return (
    <div className="space-y-6">
      {/* Metadata */}
      <div className="flex flex-wrap gap-6 text-sm text-muted-foreground">
        <span>
          Started: <span className="text-foreground">{formatDate(run.created_at)}</span>
        </span>
        {run.execution_time_seconds != null && (
          <span>
            Duration:{' '}
            <span className="font-mono text-foreground">
              {run.execution_time_seconds.toFixed(2)}s
            </span>
          </span>
        )}
        {run.slack_sent && <span className="text-green-500">Slack sent</span>}
      </div>

      {/* Results grouped in matrix card */}
      {run.results.length > 0 ? (
        <CustomerResultCard customerId={customerLabel} results={run.results} />
      ) : (
        <p className="text-sm text-muted-foreground">No results recorded</p>
      )}
    </div>
  )
}
