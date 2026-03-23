'use client'

import React from 'react'
import { Button } from '@/components/ui/button'

interface FilterBarProps {
  children: React.ReactNode
  onReset: () => void
}

export function FilterBar({ children, onReset }: FilterBarProps) {
  return (
    <div className="flex items-center gap-2">
      <div className="flex flex-1 items-center gap-2">{children}</div>
      <Button variant="ghost" size="sm" onClick={onReset}>
        Reset
      </Button>
    </div>
  )
}
