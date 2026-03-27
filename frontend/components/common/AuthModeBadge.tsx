import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'
import type { AuthMethod } from '@/lib/types/api'

const AUTH_MODE_STYLES: Record<AuthMethod, string> = {
  profile:      'bg-sky-500/20 text-sky-400 border-sky-500/30',
  access_key:   'bg-amber-500/20 text-amber-400 border-amber-500/30',
  assumed_role: 'bg-emerald-600/20 text-emerald-400 border-emerald-600/30',
}

const AUTH_MODE_LABELS: Record<AuthMethod, string> = {
  profile:      'Profile',
  access_key:   'Access Key',
  assumed_role: 'Assumed Role',
}

interface AuthModeBadgeProps {
  mode: AuthMethod
  className?: string
}

export function AuthModeBadge({ mode, className }: AuthModeBadgeProps) {
  return (
    <Badge className={cn(AUTH_MODE_STYLES[mode] ?? 'bg-muted text-muted-foreground', className)}>
      {AUTH_MODE_LABELS[mode] ?? mode}
    </Badge>
  )
}
