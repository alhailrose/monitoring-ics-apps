'use client'

import { useRouter, useSearchParams, usePathname } from 'next/navigation'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'

const WINDOWS = [
  { value: '6',  label: 'Last 6h' },
  { value: '12', label: 'Last 12h' },
  { value: '24', label: 'Last 24h' },
  { value: '48', label: 'Last 48h' },
  { value: '168', label: 'Last 7d' },
]

interface WindowSelectorProps {
  windowHours: number
}

export function WindowSelector({ windowHours }: WindowSelectorProps) {
  const router = useRouter()
  const searchParams = useSearchParams()
  const pathname = usePathname()

  const handleChange = (value: string) => {
    const params = new URLSearchParams(searchParams.toString())
    params.set('window_hours', value)
    router.replace(`${pathname}?${params.toString()}`)
  }

  return (
    <Select value={String(windowHours)} onValueChange={handleChange}>
      <SelectTrigger className="w-28">
        <SelectValue />
      </SelectTrigger>
      <SelectContent>
        {WINDOWS.map((w) => (
          <SelectItem key={w.value} value={w.value}>
            {w.label}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  )
}
