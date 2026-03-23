'use client'

import { useEffect, useState } from 'react'
import { cn } from '@/lib/utils'

interface CheckProgressProps {
  label?: string
}

const STEPS = [
  'Preparing check execution…',
  'Authenticating AWS sessions…',
  'Running checks across accounts…',
  'Collecting results…',
  'Finalizing report…',
]

export function CheckProgress({ label = 'Running checks' }: CheckProgressProps) {
  const [step, setStep] = useState(0)
  const [elapsed, setElapsed] = useState(0)

  useEffect(() => {
    const timer = setInterval(() => {
      setElapsed((e) => e + 1)
    }, 1000)
    return () => clearInterval(timer)
  }, [])

  useEffect(() => {
    // Progress through steps with increasing delays
    const delays = [2000, 4000, 6000, 15000]
    if (step < STEPS.length - 1) {
      const timeout = setTimeout(() => {
        setStep((s) => s + 1)
      }, delays[step] ?? 10000)
      return () => clearTimeout(timeout)
    }
  }, [step])

  const progress = Math.min(((step + 1) / STEPS.length) * 100, 95)

  return (
    <div className="rounded-lg border border-border bg-muted/10 p-4 space-y-3">
      <div className="flex items-center justify-between">
        <p className="text-sm font-medium text-foreground">{label}</p>
        <span className="text-xs text-muted-foreground font-mono">{elapsed}s</span>
      </div>

      {/* Progress bar */}
      <div className="h-1.5 w-full rounded-full bg-muted/40 overflow-hidden">
        <div
          className="h-full rounded-full bg-primary transition-all duration-1000 ease-out"
          style={{ width: `${progress}%` }}
        />
      </div>

      {/* Current step */}
      <div className="flex items-center gap-2">
        <div className="h-2 w-2 rounded-full bg-primary animate-pulse" />
        <p className="text-xs text-muted-foreground">{STEPS[step]}</p>
      </div>

      {/* Step indicators */}
      <div className="flex gap-1">
        {STEPS.map((_, i) => (
          <div
            key={i}
            className={cn(
              'h-1 flex-1 rounded-full transition-colors duration-500',
              i <= step ? 'bg-primary/60' : 'bg-muted/40',
            )}
          />
        ))}
      </div>
    </div>
  )
}
