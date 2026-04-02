'use client'

import Link from 'next/link'
import { useAlarms } from '@/components/providers/AlarmContext'
import { cn } from '@/lib/utils'

export function AlarmIndicator() {
  const { count, loading } = useAlarms()

  if (loading || count === 0) return null

  return (
    <Link
      href="/alarms"
      className={cn(
        'flex items-center gap-1.5 rounded-md px-2 py-1 text-xs font-medium',
        'bg-red-500/10 text-red-500 hover:bg-red-500/20 transition-colors',
      )}
      title={`${count} alarm aktif`}
    >
      {/* Pulsing dot */}
      <span className="relative flex size-2">
        <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-red-500 opacity-75" />
        <span className="relative inline-flex size-2 rounded-full bg-red-500" />
      </span>
      {count} alarm aktif
    </Link>
  )
}
