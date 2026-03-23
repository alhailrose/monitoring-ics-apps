'use client'

import { useState } from 'react'
import { HugeiconsIcon } from '@hugeicons/react'
import { Copy01Icon, CheckmarkCircle01Icon } from '@hugeicons/core-free-icons'
import { cn } from '@/lib/utils'

interface InlineCodeProps {
  children: string
  className?: string
}

export function InlineCode({ children, className }: InlineCodeProps) {
  const [copied, setCopied] = useState(false)

  const handleCopy = () => {
    navigator.clipboard.writeText(children)
    setCopied(true)
    setTimeout(() => setCopied(false), 1500)
  }

  return (
    <span className={cn('inline-flex items-center gap-1 rounded bg-muted px-1.5 py-0.5', className)}>
      <code className="font-mono text-xs">{children}</code>
      <button
        type="button"
        onClick={handleCopy}
        aria-label="Copy to clipboard"
        className="text-muted-foreground hover:text-foreground transition-colors"
      >
        <HugeiconsIcon
          icon={copied ? CheckmarkCircle01Icon : Copy01Icon}
          className="size-3"
          strokeWidth={2}
        />
      </button>
    </span>
  )
}
