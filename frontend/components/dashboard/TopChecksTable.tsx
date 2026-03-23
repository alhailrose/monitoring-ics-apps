import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { EmptyState } from '@/components/common/EmptyState'
import type { DashboardSummary } from '@/lib/types/api'

interface TopChecksTableProps {
  checks: DashboardSummary['top_checks']
}

export function TopChecksTable({ checks }: TopChecksTableProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-sm font-medium">Top Checks</CardTitle>
      </CardHeader>
      <CardContent>
        {checks.length === 0 ? (
          <EmptyState
            title="No checks run yet"
            description="Run a check to see activity here"
          />
        ) : (
          <ul className="space-y-2">
            {checks.map((item) => (
              <li key={item.check_name} className="flex items-center justify-between text-sm">
                <span className="truncate text-foreground">{item.check_name}</span>
                <span className="ml-4 shrink-0 tabular-nums text-muted-foreground">
                  {item.runs} run{item.runs !== 1 ? 's' : ''}
                </span>
              </li>
            ))}
          </ul>
        )}
      </CardContent>
    </Card>
  )
}
