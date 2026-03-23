'use client'

import { Badge } from '@/components/ui/badge'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip'
import { InlineCode } from '@/components/common/InlineCode'
import type { SessionStatus } from '@/lib/types/api'

const SESSION_STATUS_STYLES: Record<SessionStatus, string> = {
  ok:        'bg-green-600/20 text-green-400 border-green-600/30',
  expired:   'bg-red-600/20 text-red-400 border-red-600/30',
  no_config: 'bg-slate-500/20 text-slate-400 border-slate-500/30',
  error:     'bg-orange-500/20 text-orange-400 border-orange-500/30',
}

interface SessionStatusBadgeProps {
  status: SessionStatus
  loginCommand?: string
}

export function SessionStatusBadge({ status, loginCommand }: SessionStatusBadgeProps) {
  const badge = <Badge className={SESSION_STATUS_STYLES[status]}>{status}</Badge>

  if (status === 'expired' && loginCommand) {
    return (
      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger asChild>{badge}</TooltipTrigger>
          <TooltipContent>
            <InlineCode>{loginCommand}</InlineCode>
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>
    )
  }

  return badge
}
