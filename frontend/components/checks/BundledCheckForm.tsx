'use client'
// Client component — needs useState/useTransition for customer selection and results

import { useEffect, useRef, useState, useTransition } from 'react'
import { toast } from 'sonner'
import { runChecks } from '@/app/(dashboard)/checks/actions'
import { CheckProgress } from '@/components/checks/CheckProgress'
import { ResultsTable } from '@/components/checks/ResultsTable'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import Link from 'next/link'
import { cn } from '@/lib/utils'
import type { Customer, ExecuteResponse } from '@/lib/types/api'

const MODES = [
  { value: 'all',   label: 'All Checks' },
  { value: 'arbel', label: 'Arbel Suite' },
]

interface BundledCheckFormProps {
  customers: Customer[]
}

export function BundledCheckForm({ customers }: BundledCheckFormProps) {
  const [selectedCustomerIds, setSelectedCustomerIds] = useState<string[]>([])
  const [selectedMode, setSelectedMode] = useState(MODES[0].value)
  const [results, setResults] = useState<ExecuteResponse | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [isPending, startTransition] = useTransition()
  const resultAnchorRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    if (!results) return
    if (typeof resultAnchorRef.current?.scrollIntoView === 'function') {
      resultAnchorRef.current.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }
  }, [results])

  const toggleCustomer = (id: string) => {
    setSelectedCustomerIds((prev) =>
      prev.includes(id) ? prev.filter((c) => c !== id) : [...prev, id],
    )
  }

  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()

    const formData = new FormData(e.currentTarget)

    setError(null)
    setResults(null)
    startTransition(async () => {
      const res = await runChecks(formData)
      if (res.error) {
        setError(res.error)
        toast.error('Check failed', { description: res.error })
      } else if (res.data) {
        setResults(res.data)
        const total = res.data.results.length
        const ok = res.data.results.filter((r) => r.status === 'OK').length
        toast.success('Checks completed', {
          description: `${ok}/${total} passed`,
        })
      }
    })
  }

  const hasCustomer = selectedCustomerIds.length > 0
  const latestRunId = results?.check_run_id ?? results?.check_runs?.[0]?.check_run_id ?? null
  const runBlockedReason = !hasCustomer
    ? 'Select at least one customer'
    : null

  return (
    <div className="space-y-6">
      <form onSubmit={handleSubmit} className="space-y-5">
        <input type="hidden" name="send_slack" value="false" />
        <input type="hidden" name="mode" value={selectedMode} />
        {selectedCustomerIds.map((id) => (
          <input key={id} type="hidden" name="customer_ids" value={id} />
        ))}

        {/* Mode select */}
        <div className="space-y-1.5 max-w-xs">
          <Label htmlFor="bundled-mode-select">Mode</Label>
          <Select value={selectedMode} onValueChange={setSelectedMode}>
            <SelectTrigger id="bundled-mode-select">
              <SelectValue placeholder="Select mode" />
            </SelectTrigger>
            <SelectContent>
              {MODES.map((m) => (
                <SelectItem key={m.value} value={m.value}>
                  {m.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <p className="text-xs text-muted-foreground">
            {selectedMode === 'all'
              ? 'Runs every configured check for each selected customer'
              : 'Runs the Arbel daily reporting suite (utilization, budget, alarms)'}
          </p>
        </div>

        {/* Customer toggle buttons */}
        <div className="space-y-1.5">
          <div className="flex items-center justify-between">
            <Label>Customers</Label>
            {customers.length > 0 && (
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => setSelectedCustomerIds(customers.map((c) => c.id))}
                  className="text-xs text-muted-foreground hover:text-foreground transition-colors"
                >
                  Select All
                </button>
                {selectedCustomerIds.length > 0 && (
                  <>
                    <span className="text-xs text-muted-foreground">·</span>
                    <button
                      type="button"
                      onClick={() => setSelectedCustomerIds([])}
                      className="text-xs text-muted-foreground hover:text-foreground transition-colors"
                    >
                      Clear
                    </button>
                  </>
                )}
              </div>
            )}
          </div>
          {customers.length === 0 ? (
            <p className="text-xs text-muted-foreground">
              No customers available.{' '}
              <Link href="/customers" className="underline underline-offset-2 hover:text-foreground">
                Add one in Customers
              </Link>
            </p>
          ) : (
            <div className="flex flex-wrap gap-2">
              {customers.map((c) => {
                const active = selectedCustomerIds.includes(c.id)
                return (
                  <button
                    key={c.id}
                    type="button"
                    onClick={() => toggleCustomer(c.id)}
                    className={cn(
                      'rounded-md border px-3 py-1.5 text-xs font-medium transition-colors',
                      active
                        ? 'border-primary bg-primary/10 text-primary'
                        : 'border-border bg-muted/30 text-muted-foreground hover:border-primary/50',
                    )}
                  >
                    {c.display_name}
                  </button>
                )
              })}
            </div>
          )}
          <p className="text-xs text-muted-foreground">
            {!hasCustomer
              ? 'Select at least one customer to run.'
              : `${selectedCustomerIds.length} customer${selectedCustomerIds.length !== 1 ? 's' : ''} selected`}
          </p>
        </div>

        {error && <p className="text-sm text-red-400">{error}</p>}

        <Button type="submit" disabled={isPending || !!runBlockedReason}>
          {isPending ? 'Running…' : 'Run Checks'}
        </Button>
        {runBlockedReason && (
          <p className="text-xs text-amber-300">Run blocked: {runBlockedReason}</p>
        )}
      </form>

      {isPending && <CheckProgress label="Running bundled checks…" />}
      {results && (
        <div ref={resultAnchorRef} className="space-y-3">
          <div className="rounded-md border border-border/60 bg-muted/20 px-3 py-2">
            <p className="text-xs text-muted-foreground">
              Run completed. Review the results below.
            </p>
            {latestRunId ? (
              <Link href={`/history?run=${latestRunId}`} className="text-xs font-medium underline underline-offset-2">
                View latest run
              </Link>
            ) : null}
          </div>
          <ResultsTable data={results} />
        </div>
      )}
    </div>
  )
}
