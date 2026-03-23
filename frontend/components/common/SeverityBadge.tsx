import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'
import type { FindingSeverity } from '@/lib/types/api'

const SEVERITY_STYLES: Record<FindingSeverity, string> = {
  CRITICAL: 'bg-red-700/20 text-red-300 border-red-700/30',
  HIGH:     'bg-orange-500/20 text-orange-400 border-orange-500/30',
  MEDIUM:   'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
  LOW:      'bg-blue-400/20 text-blue-400 border-blue-400/30',
  INFO:     'bg-slate-400/20 text-slate-400 border-slate-400/30',
  ALARM:    'bg-red-500/20 text-red-300 border-red-500/30',
}

interface SeverityBadgeProps {
  severity: FindingSeverity
  className?: string
}

export function SeverityBadge({ severity, className }: SeverityBadgeProps) {
  return (
    <Badge className={cn(SEVERITY_STYLES[severity], className)}>
      {severity}
    </Badge>
  )
}
