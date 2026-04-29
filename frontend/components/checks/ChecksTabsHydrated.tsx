'use client'

import { useEffect, useState } from 'react'
import { ChecksTabs } from '@/components/checks/ChecksTabs'
import type { Customer } from '@/lib/types/api'

interface ChecksTabsHydratedProps {
  customers: Customer[]
}

export function ChecksTabsHydrated({ customers }: ChecksTabsHydratedProps) {
  const [mounted, setMounted] = useState(false)

  useEffect(() => {
    setMounted(true)
  }, [])

  if (!mounted) {
    return <div className="rounded-md border border-border/50 px-3 py-2 text-xs text-muted-foreground">Loading checks tabs...</div>
  }

  return <ChecksTabs customers={customers} />
}
