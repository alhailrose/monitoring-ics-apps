'use client'

import { Badge } from '@/components/ui/badge'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip'
import { InlineCode } from '@/components/common/InlineCode'
import type { ErrorClass } from '@/lib/types/api'

const ERROR_CLASS_LABELS: Record<NonNullable<ErrorClass>, { label: string; style: string }> = {
  sso_expired:         { label: 'Login required',      style: 'bg-red-500/20 text-red-300' },
  assume_role_failed:  { label: 'Access denied',       style: 'bg-orange-500/20 text-orange-300' },
  invalid_credentials: { label: 'Invalid credentials', style: 'bg-amber-500/20 text-amber-300' },
  no_config:           { label: 'Not configured',      style: 'bg-slate-500/20 text-slate-400' },
}

interface AuthErrorBadgeProps {
  errorClass: ErrorClass
  loginCommand?: string
}

export function AuthErrorBadge({ errorClass, loginCommand }: AuthErrorBadgeProps) {
  if (!errorClass) return null

  const { label, style } = ERROR_CLASS_LABELS[errorClass]

  const badge = <Badge className={style}>{label}</Badge>

  if (!loginCommand) return badge

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
