'use client'
// Icon button in the top header bar — toggles the floating terminal drawer

import { HugeiconsIcon } from '@hugeicons/react'
import { CommandLineIcon } from '@hugeicons/core-free-icons'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'
import { useTerminal } from '@/components/terminal/TerminalContext'

export function TerminalToggleButton() {
  const { open, toggle } = useTerminal()
  return (
    <Button
      variant="ghost"
      size="icon"
      onClick={toggle}
      aria-label="Toggle terminal"
      className={cn(
        'h-8 w-8 text-muted-foreground hover:text-foreground transition-colors',
        open && 'text-primary bg-primary/10 hover:text-primary',
      )}
    >
      <HugeiconsIcon icon={CommandLineIcon} strokeWidth={2} className="size-4" />
    </Button>
  )
}
