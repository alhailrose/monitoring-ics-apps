'use client'

import { Fragment, useState, useCallback } from 'react'
import dynamic from 'next/dynamic'
import { HugeiconsIcon } from '@hugeicons/react'
import { Copy01Icon, CheckmarkCircle01Icon } from '@hugeicons/core-free-icons'
import { StatusBadge } from '@/components/common/StatusBadge'
import { AuthErrorBadge } from '@/components/common/AuthErrorBadge'
import { cn } from '@/lib/utils'
import type { CheckResult } from '@/lib/types/api'


const CheckDetailView = dynamic(
  () => import('@/components/checks/CheckDetailView').then((m) => m.CheckDetailView),
  { ssr: false },
)

function CopyCellButton({ result }: { result: CheckResult }) {
  const [copied, setCopied] = useState(false)

  const text = result.output ?? result.summary ?? ''

  const handleCopy = useCallback(
    (e: React.MouseEvent) => {
      e.stopPropagation() // don't toggle the expand
      if (!text) return
      navigator.clipboard.writeText(text).then(() => {
        setCopied(true)
        setTimeout(() => setCopied(false), 1500)
      })
    },
    [text],
  )

  if (!text) return null

  return (
    <button
      type="button"
      onClick={handleCopy}
      title={copied ? 'Copied!' : 'Copy output'}
      className={cn(
        'opacity-0 group-hover:opacity-100 transition-opacity',
        'rounded p-0.5 hover:bg-muted/60',
        copied && 'opacity-100',
      )}
    >
      <HugeiconsIcon
        icon={copied ? CheckmarkCircle01Icon : Copy01Icon}
        strokeWidth={1.5}
        className={cn('size-3', copied ? 'text-green-400' : 'text-muted-foreground')}
      />
    </button>
  )
}

interface CustomerResultCardProps {
  customerId: string
  results: CheckResult[]
}

export function CustomerResultCard({ customerId, results }: CustomerResultCardProps) {
  const [expandedCell, setExpandedCell] = useState<string | null>(null)

  // Derive unique accounts and checks from results
  const accountMap = new Map<string, { id: string; display_name: string; profile_name: string }>()
  const checkNames: string[] = []
  const resultMap = new Map<string, CheckResult>()

  for (const r of results) {
    if (!accountMap.has(r.account.id)) {
      accountMap.set(r.account.id, r.account)
    }
    if (!checkNames.includes(r.check_name)) {
      checkNames.push(r.check_name)
    }
    resultMap.set(`${r.check_name}:${r.account.id}`, r)
  }

  const accounts = Array.from(accountMap.values())
  const okCount = results.filter((r) => r.status === 'OK').length
  const warnCount = results.filter((r) => r.status === 'WARN' || r.status === 'ALARM').length
  const errorCount = results.filter((r) => r.status === 'ERROR').length

  const toggleCell = (key: string) => {
    setExpandedCell(expandedCell === key ? null : key)
  }

  const expandedResult = expandedCell ? resultMap.get(expandedCell) : null

  return (
    <div className="rounded-lg border border-border overflow-hidden">
      {/* Card header */}
      <div className="flex items-center justify-between px-4 py-2.5 bg-muted/30 border-b border-border">
        <span className="text-sm font-medium">{customerId}</span>
        <div className="flex items-center gap-2 text-xs">
          {okCount > 0 && (
            <span className="flex items-center gap-1">
              <StatusBadge status="OK" /> {okCount}
            </span>
          )}
          {warnCount > 0 && (
            <span className="flex items-center gap-1">
              <StatusBadge status="WARN" /> {warnCount}
            </span>
          )}
          {errorCount > 0 && (
            <span className="flex items-center gap-1">
              <StatusBadge status="ERROR" /> {errorCount}
            </span>
          )}
        </div>
      </div>

      {/* Matrix table */}
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border bg-muted/20">
              <th className="px-4 py-2 text-left font-medium text-muted-foreground text-xs">
                Check
              </th>
              {accounts.map((a) => (
                <th
                  key={a.id}
                  className="px-3 py-2 text-center font-medium text-muted-foreground text-xs"
                >
                  {a.display_name}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {checkNames.map((checkName) => {
              const expandedInRow = accounts.find(
                (a) => expandedCell === `${checkName}:${a.id}`,
              )

              return (
                <Fragment key={checkName}>
                  <tr className="border-b border-border last:border-0">
                    <td className="px-4 py-2 text-xs text-muted-foreground">{checkName}</td>
                    {accounts.map((a) => {
                      const cellKey = `${checkName}:${a.id}`
                      const r = resultMap.get(cellKey)
                      return (
                        <td
                          key={cellKey}
                          onClick={() => r && toggleCell(cellKey)}
                          className={cn(
                            'px-3 py-2 text-center cursor-pointer hover:bg-muted/20 transition-colors',
                            expandedCell === cellKey && 'bg-muted/10',
                          )}
                        >
                          {r ? (
                            <div className="inline-flex flex-col items-center gap-0.5 group">
                              <div className="inline-flex items-center gap-1">
                                <StatusBadge status={r.status} />
                                {r.error_class && <AuthErrorBadge errorClass={r.error_class} />}
                                <CopyCellButton result={r} />
                              </div>
                              <span className={cn(
                                'text-[9px] text-muted-foreground/50 group-hover:text-muted-foreground transition-colors',
                                expandedCell === cellKey && 'text-muted-foreground',
                              )}>
                                {expandedCell === cellKey ? '▴ close' : '▾ detail'}
                              </span>
                            </div>
                          ) : (
                            <span className="text-xs text-muted-foreground">—</span>
                          )}
                        </td>
                      )
                    })}
                  </tr>

                  {/* Expanded detail row */}
                  {expandedInRow && expandedResult && (
                    <tr className="border-b border-border last:border-0">
                      <td colSpan={accounts.length + 1} className="px-4 py-3 bg-muted/5">
                        <div className="space-y-1">
                          <div className="flex items-center gap-2 text-xs text-muted-foreground mb-2">
                            <span className="font-medium text-foreground">
                              {expandedInRow.display_name}
                            </span>
                            <span>·</span>
                            <span>{expandedResult.check_name}</span>
                            {expandedResult.summary && (
                              <>
                                <span>·</span>
                                <span>{expandedResult.summary}</span>
                              </>
                            )}
                          </div>
                          {expandedResult.details ? (
                            <CheckDetailView
                              checkName={expandedResult.check_name}
                              details={expandedResult.details}
                            />
                          ) : expandedResult.output ? (
                            <pre className="whitespace-pre-wrap text-xs text-muted-foreground font-mono leading-relaxed max-h-80 overflow-y-auto">
                              {expandedResult.output}
                            </pre>
                          ) : (
                            <p className="text-xs text-muted-foreground italic">No output</p>
                          )}
                        </div>
                      </td>
                    </tr>
                  )}
                </Fragment>
              )
            })}
          </tbody>
        </table>
      </div>

    </div>
  )
}
