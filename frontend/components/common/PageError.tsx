'use client'

import { useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { HugeiconsIcon } from '@hugeicons/react'
import { AlertCircleIcon, RefreshIcon } from '@hugeicons/core-free-icons'

interface PageErrorProps {
  error: Error & { digest?: string }
  reset: () => void
  title?: string
}

export function PageError({ error, reset, title = 'Something went wrong' }: PageErrorProps) {
  useEffect(() => {
    console.error(error)
  }, [error])

  return (
    <div className="flex flex-col items-center justify-center gap-4 p-12 text-center">
      <div className="rounded-full bg-destructive/10 p-4">
        <HugeiconsIcon icon={AlertCircleIcon} className="h-8 w-8 text-destructive" />
      </div>
      <div className="space-y-1">
        <p className="font-semibold">{title}</p>
        <p className="text-sm text-muted-foreground">
          Failed to load data. Please try again.
        </p>
      </div>
      <Button variant="outline" size="sm" onClick={reset}>
        <HugeiconsIcon icon={RefreshIcon} className="mr-2 h-4 w-4" />
        Retry
      </Button>
    </div>
  )
}
