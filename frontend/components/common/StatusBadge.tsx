import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'
import type { CheckStatus } from '@/lib/types/api'

const STATUS_STYLES: Record<CheckStatus, string> = {
  OK:      'bg-green-600/20 text-green-400 border-green-600/30',
  WARN:    'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
  ERROR:   'bg-red-600/20 text-red-400 border-red-600/30',
  ALARM:   'bg-red-500/20 text-red-300 border-red-500/30',
  NO_DATA: 'bg-slate-500/20 text-slate-400 border-slate-500/30',
}

interface StatusBadgeProps {
  status: CheckStatus
  className?: string
}

export function StatusBadge({ status, className }: StatusBadgeProps) {
  return (
    <Badge className={cn(STATUS_STYLES[status], className)}>
      {status}
    </Badge>
  )
}
