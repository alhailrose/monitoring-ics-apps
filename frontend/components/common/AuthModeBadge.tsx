import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'
import type { AwsAuthMode } from '@/lib/types/api'

const AUTH_MODE_STYLES: Record<AwsAuthMode, string> = {
  assume_role: 'bg-emerald-600/20 text-emerald-400 border-emerald-600/30',
  sso:         'bg-sky-500/20 text-sky-400 border-sky-500/30',
  aws_login:   'bg-slate-500/20 text-slate-400 border-slate-500/30',
  access_key:  'bg-amber-500/20 text-amber-400 border-amber-500/30',
}

interface AuthModeBadgeProps {
  mode: AwsAuthMode
  className?: string
}

export function AuthModeBadge({ mode, className }: AuthModeBadgeProps) {
  return (
    <Badge className={cn(AUTH_MODE_STYLES[mode], className)}>
      {mode}
    </Badge>
  )
}
