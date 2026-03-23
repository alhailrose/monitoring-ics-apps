'use client'

import { AuthModeBadge } from '@/components/common/AuthModeBadge'
import { SessionStatusBadge } from '@/components/common/SessionStatusBadge'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Skeleton } from '@/components/ui/skeleton'
import { HugeiconsIcon } from '@hugeicons/react'
import { MoreHorizontalIcon, PencilEdit01Icon, Delete01Icon } from '@hugeicons/core-free-icons'
import { cn } from '@/lib/utils'
import type { Account, ProfileHealth } from '@/lib/types/api'

interface AccountRowProps {
  account: Account
  healthMap: Record<string, ProfileHealth>
  healthLoading?: boolean
  role: string
  onEdit: (a: Account) => void
  onDelete: (id: string) => void
}

export function AccountRow({
  account,
  healthMap,
  healthLoading = false,
  role,
  onEdit,
  onDelete,
}: AccountRowProps) {
  const health = healthMap[account.profile_name]

  return (
    <div
      className={cn(
        'grid grid-cols-[1fr_auto] sm:grid-cols-[1fr_120px_100px_auto] gap-x-3 items-center px-3 py-2',
        'border-b border-border/30 last:border-0',
        'hover:bg-muted/20 transition-colors',
      )}
    >
      {/* Account info */}
      <div className="min-w-0">
        <div className="flex items-center gap-2">
          <p className="text-sm font-medium text-foreground truncate">{account.display_name}</p>
          {!account.is_active && (
            <span className="shrink-0 text-[10px] text-amber-400 border border-amber-400/30 bg-amber-400/10 rounded px-1 py-px">
              inactive
            </span>
          )}
        </div>
        <div className="flex items-center gap-1.5 mt-0.5">
          <p className="text-[11px] text-muted-foreground font-mono">{account.account_id}</p>
          <span className="text-muted-foreground/30">·</span>
          <p className="text-[11px] text-muted-foreground/60 font-mono">{account.profile_name}</p>
        </div>
      </div>

      {/* Auth mode — hidden on mobile */}
      <div className="hidden sm:flex justify-center">
        <AuthModeBadge mode={account.aws_auth_mode} />
      </div>

      {/* Session status — hidden on mobile */}
      <div className="hidden sm:flex justify-center">
        {healthLoading ? (
          <Skeleton className="h-5 w-14 rounded-full" />
        ) : health ? (
          <SessionStatusBadge status={health.status} loginCommand={health.login_command} />
        ) : (
          <span className="text-xs text-muted-foreground/40">—</span>
        )}
      </div>

      {/* Actions */}
      {role === 'super_user' ? (
        <div className="flex justify-end w-8">
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                className="h-7 w-7 text-muted-foreground hover:text-foreground"
              >
                <HugeiconsIcon icon={MoreHorizontalIcon} strokeWidth={2} className="size-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-36">
              <DropdownMenuItem onClick={() => onEdit(account)}>
                <HugeiconsIcon icon={PencilEdit01Icon} strokeWidth={2} className="size-4 mr-2" />
                Edit
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem
                className="text-destructive focus:text-destructive"
                onClick={() => onDelete(account.id)}
              >
                <HugeiconsIcon icon={Delete01Icon} strokeWidth={2} className="size-4 mr-2" />
                Delete
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      ) : (
        <div className="w-8" />
      )}
    </div>
  )
}
