'use client'

import { useState, useCallback } from 'react'
import { HugeiconsIcon } from '@hugeicons/react'
import { Copy01Icon, CheckmarkCircle01Icon } from '@hugeicons/core-free-icons'
import { CustomerResultCard } from '@/components/checks/CustomerResultCard'
import { cn } from '@/lib/utils'
import type { ExecuteResponse, CheckResult } from '@/lib/types/api'

interface ResultsTableProps {
  data: ExecuteResponse
}

function CopyButton({ text, className }: { text: string; className?: string }) {
  const [copied, setCopied] = useState(false)

  const handleCopy = useCallback(
    (e: React.MouseEvent) => {
      e.stopPropagation()
      navigator.clipboard.writeText(text)
      setCopied(true)
      setTimeout(() => setCopied(false), 1500)
    },
    [text],
  )

  return (
    <button
      type="button"
      onClick={handleCopy}
      aria-label="Copy to clipboard"
      className={cn(
        'inline-flex items-center gap-1 rounded-md px-2 py-1 text-xs text-muted-foreground hover:text-foreground hover:bg-muted/40 transition-colors',
        className,
      )}
    >
      <HugeiconsIcon
        icon={copied ? CheckmarkCircle01Icon : Copy01Icon}
        className="size-3.5"
        strokeWidth={2}
      />
      {copied ? 'Copied' : 'Copy'}
    </button>
  )
}

export function ResultsTable({ data }: ResultsTableProps) {
  // Group results by customer_id
  const grouped = new Map<string, CheckResult[]>()
  for (const r of data.results) {
    const key = r.customer_id
    if (!grouped.has(key)) grouped.set(key, [])
    grouped.get(key)!.push(r)
  }

  return (
    <div className="space-y-4">
      <p className="text-xs text-muted-foreground">
        Completed in {data.execution_time_seconds.toFixed(2)}s
        {' · '}
        {data.results.length} result{data.results.length !== 1 ? 's' : ''}
      </p>

      {/* Customer cards */}
      {Array.from(grouped.entries()).map(([customerId, results]) => (
        <CustomerResultCard key={customerId} customerId={customerId} results={results} />
      ))}

      {/* Consolidated outputs (for bundled/arbel modes) */}
      {Object.keys(data.consolidated_outputs).length > 0 && (
        <div className="space-y-3">
          <p className="text-xs font-medium text-muted-foreground">Consolidated Reports</p>
          {Object.entries(data.consolidated_outputs).map(([customerId, output]) => (
            <details key={customerId} className="rounded-lg border border-border">
              <summary className="flex items-center justify-between px-4 py-2 cursor-pointer hover:bg-muted/20 transition-colors list-none">
                <span className="text-sm font-medium">Report — {customerId}</span>
                <div className="flex items-center gap-1" onClick={(e) => e.stopPropagation()}>
                  <CopyButton text={output} />
                  <span className="text-xs text-muted-foreground/50 select-none pl-1">▾</span>
                </div>
              </summary>
              <div className="px-4 py-3 border-t border-border/50">
                <pre className="whitespace-pre-wrap text-xs text-muted-foreground font-mono leading-relaxed max-h-96 overflow-y-auto">
                  {output}
                </pre>
              </div>
            </details>
          ))}
        </div>
      )}
    </div>
  )
}
