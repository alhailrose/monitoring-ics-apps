'use client'

import { useState, useCallback } from 'react'
import { HugeiconsIcon } from '@hugeicons/react'
import { Copy01Icon, CheckmarkCircle01Icon } from '@hugeicons/core-free-icons'
import { CustomerResultCard } from '@/components/checks/CustomerResultCard'
import { cn } from '@/lib/utils'
import type { ExecuteResponse, CheckResult } from '@/lib/types/api'

// ── Pelaporan helpers ─────────────────────────────────────────────────────────

interface ReportAlarm {
  alarm_name?: string
  threshold_text?: string
  breach_start_time?: string
  ongoing_minutes?: number
  recommended_action?: string
}

type ReportItem =
  | { type: 'bullet'; text: string }
  | { type: 'block'; text: string }  // prose paragraph, no bullet prefix

interface ReportGroup {
  accountName: string
  items: ReportItem[]
}

const BULAN_ID = [
  'Januari', 'Februari', 'Maret', 'April', 'Mei', 'Juni',
  'Juli', 'Agustus', 'September', 'Oktober', 'November', 'Desember',
]

function formatTanggalID(dateStr: string): string {
  // dateStr is YYYY-MM-DD (UTC date from AWS)
  const parts = dateStr.split('-')
  if (parts.length !== 3) return dateStr
  const d = parseInt(parts[2], 10)
  const m = parseInt(parts[1], 10) - 1
  const y = parts[0]
  return `${d} ${BULAN_ID[m] ?? ''} ${y}`
}

function durationDays(start: string, end: string): number {
  const s = new Date(start).getTime()
  const e = new Date(end).getTime()
  if (isNaN(s) || isNaN(e)) return 1
  return Math.max(1, Math.round((e - s) / (1000 * 60 * 60 * 24)) + 1)
}

function greeting(): string {
  // WIB = UTC+7
  const wibHour = (new Date().getUTCHours() + 7) % 24
  if (wibHour >= 5 && wibHour < 11) return 'Selamat Pagi'
  if (wibHour >= 11 && wibHour < 15) return 'Selamat Siang'
  if (wibHour >= 15 && wibHour < 18) return 'Selamat Sore'
  return 'Selamat Malam'
}

function joinId(arr: string[], max = 4): string {
  const shown = arr.slice(0, max)
  if (shown.length <= 1) return shown[0] ?? ''
  return shown.slice(0, -1).join(', ') + ' dan ' + shown[shown.length - 1]
}

function buildCheckReportItems(result: CheckResult): ReportItem[] {
  const items: ReportItem[] = []
  const d = result.details
  if (!d) return items

  if (result.check_name === 'alarm_verification') {
    const alarms = (d.alarms ?? []) as ReportAlarm[]
    for (const a of alarms.filter((a) => a.recommended_action === 'REPORT_NOW')) {
      const startText =
        a.breach_start_time === 'unknown'
          ? ', sudah > 24 jam (alarm kronis)'
          : a.breach_start_time
          ? `, sejak ${a.breach_start_time}`
          : a.ongoing_minutes && a.ongoing_minutes > 0
          ? `, sudah ${a.ongoing_minutes} menit`
          : ''
      items.push({ type: 'bullet', text: `Alarm *${a.alarm_name ?? '-'}* (${a.threshold_text ?? '-'})${startText}` })
    }
  } else if (result.check_name === 'cost') {
    const anomalies = (d.anomalies ?? []) as Array<Record<string, unknown>>
    const accountName = result.account.display_name

    for (const a of anomalies) {
      const impact = (a.Impact as Record<string, unknown>) ?? {}
      const totalImpact = Number(impact.TotalImpact ?? 0)
      const actualSpend = Number(impact.TotalActualSpend ?? 0)
      const expectedSpend = Number(impact.TotalExpectedSpend ?? 0)
      const impactPct = Number(impact.TotalImpactPercentage ?? 0)
      const monitorName = (a.MonitorName as string) ?? 'N/A'
      const startDate = (a.AnomalyStartDate as string) ?? ''
      const endDate = (a.AnomalyEndDate as string) ?? ''
      const rootCauses = (a.RootCauses ?? []) as Array<Record<string, unknown>>

      const dur = startDate && endDate ? durationDays(startDate, endDate) : 1
      const tanggal = startDate ? formatTanggalID(startDate) : 'N/A'

      const para: string[] = []

      // ── Intro ──
      para.push(`kami informasikan saat ini AWS mendeteksi adanya Cost Anomaly pada account *${accountName}* dengan detail sebagai berikut.`)
      para.push('')

      // ── Spend narrative ──
      let spendLine = `Berdasarkan hasil monitoring *${monitorName}*, tercatat anomali terdeteksi pada ${tanggal} dengan durasi ${dur} hari.`
      if (actualSpend > 0 && expectedSpend > 0) {
        const pctText = impactPct > 0 ? ` atau sekitar ${impactPct.toFixed(2)}% di atas estimasi` : ''
        spendLine += ` Expected spend sebesar USD ${expectedSpend.toFixed(2)}, sedangkan actual spend mencapai USD ${actualSpend.toFixed(2)}, sehingga terdapat total cost impact sebesar USD ${totalImpact.toFixed(2)}${pctText}.`
      } else if (totalImpact > 0) {
        spendLine += ` Total cost impact: USD ${totalImpact.toFixed(2)}.`
      }
      para.push(spendLine)

      // ── Root cause prose ──
      if (rootCauses.length > 0) {
        const svcMap = new Map<string, { region: string; usageAccounts: Map<string, string[]> }>()
        for (const rc of rootCauses) {
          const svc = (rc.Service as string) ?? 'Unknown'
          const region = (rc.Region as string) ?? ''
          const usageType = (rc.UsageType as string) ?? ''
          const account = (rc.LinkedAccountName as string) || (rc.LinkedAccount as string) || ''
          if (!svcMap.has(svc)) svcMap.set(svc, { region, usageAccounts: new Map() })
          const entry = svcMap.get(svc)!
          if (usageType) {
            if (!entry.usageAccounts.has(usageType)) entry.usageAccounts.set(usageType, [])
            if (account && !entry.usageAccounts.get(usageType)!.includes(account))
              entry.usageAccounts.get(usageType)!.push(account)
          }
        }

        const svcEntries = Array.from(svcMap.entries())
        const rcSentences: string[] = []
        for (const [svc, { region, usageAccounts }] of svcEntries) {
          const regionText = region ? ` di region ${region}` : ''
          const usageEntries = Array.from(usageAccounts.entries())
          if (usageEntries.length === 0) {
            rcSentences.push(`${svc}${regionText}`)
          } else if (usageEntries.length === 1) {
            const [usageType, accounts] = usageEntries[0]
            const acctText = accounts.length > 0 ? ` dari akun ${joinId(accounts)}` : ''
            rcSentences.push(`${svc}${regionText}, komponen ${usageType}${acctText}`)
          } else {
            const usageParts = usageEntries.map(([ut, accts]) => {
              const acctText = accts.length > 0 ? ` (${joinId(accts)})` : ''
              return `${ut}${acctText}`
            })
            rcSentences.push(`${svc}${regionText}: ${usageParts.join('; ')}`)
          }
        }

        para.push('')
        para.push(`Dari hasil pengecekan pada potential root causes, anomali biaya ini didominasi oleh layanan ${rcSentences.join('. Selain itu, terdapat kontribusi dari ')}.`)
      }

      items.push({ type: 'block', text: para.join('\n') })
    }
  } else if (result.check_name === 'guardduty') {
    const findings = (d.findings as number) ?? 0
    if (findings > 0) {
      items.push({ type: 'bullet', text: `GuardDuty: ${findings} finding terdeteksi` })
    }
  } else if (result.check_name === 'cloudwatch') {
    const count = (d.count as number) ?? 0
    if (count > 0) {
      const alarmDetails = (d.details ?? []) as Array<Record<string, string>>
      const names = alarmDetails.slice(0, 3).map((a) => a.name).filter(Boolean)
      const nameText =
        names.length > 0 ? ` (${names.join(', ')}${alarmDetails.length > 3 ? ', ...' : ''})` : ''
      items.push({ type: 'bullet', text: `CloudWatch: ${count} alarm aktif${nameText}` })
    }
  } else if (result.check_name === 'backup') {
    const failed = (d.failed_jobs as number) ?? 0
    if (failed > 0) {
      items.push({ type: 'bullet', text: `Backup: ${failed} job gagal` })
    }
  } else if (result.check_name === 'notifications') {
    const recentCount = (d.recent_count as number) ?? 0
    if (recentCount > 0) {
      items.push({ type: 'bullet', text: `Notifikasi: ${recentCount} event baru (12 jam terakhir)` })
    }
  }

  return items
}

function buildCombinedReport(groups: ReportGroup[]): string {
  const salam = greeting()

  // Separate bullets and blocks across all groups
  const bulletLines: string[] = []
  const blockTexts: string[] = []
  const multiAccount = groups.filter((g) => g.items.some((i) => i.type === 'bullet')).length > 1

  for (const g of groups) {
    const groupBullets = g.items.filter((i) => i.type === 'bullet')
    const groupBlocks = g.items.filter((i) => i.type === 'block')
    if (groupBullets.length > 0) {
      if (multiAccount) bulletLines.push(`[${g.accountName}]`)
      for (const item of groupBullets) bulletLines.push(`• ${item.text}`)
    }
    for (const item of groupBlocks) blockTexts.push(item.text)
  }

  if (bulletLines.length === 0 && blockTexts.length === 0) return ''

  const parts: string[] = []

  if (bulletLines.length > 0) {
    parts.push(`${salam}, kami informasikan alarm berikut sedang melewati threshold:\n`)
    parts.push(...bulletLines)
  }

  if (blockTexts.length > 0) {
    if (bulletLines.length > 0) parts.push('')
    // First block gets the greeting prepended (lowercase continuation)
    blockTexts[0] = `${salam}, ${blockTexts[0]}`
    parts.push(...blockTexts.map((b, i) => (i > 0 ? '\n' + b : b)))
  }

  return parts.join('\n')
}

function PelaporanSection({ results }: { results: CheckResult[] }) {
  const [copied, setCopied] = useState(false)

  // Build per-account groups from all check results
  const accountGroups = new Map<string, ReportGroup>()
  for (const r of results) {
    const items = buildCheckReportItems(r)
    if (items.length === 0) continue
    const key = r.account.id
    if (!accountGroups.has(key)) {
      accountGroups.set(key, { accountName: r.account.display_name, items: [] })
    }
    accountGroups.get(key)!.items.push(...items)
  }

  const text = buildCombinedReport(Array.from(accountGroups.values()))

  return (
    <div className="rounded-lg border border-border overflow-hidden">
      <div className="flex items-center justify-between px-4 py-2.5 bg-muted/30 border-b border-border">
        <span className="text-sm font-medium">Pelaporan</span>
        {text && (
          <button
            type="button"
            onClick={() => {
              navigator.clipboard.writeText(text)
              setCopied(true)
              setTimeout(() => setCopied(false), 1500)
            }}
            className={cn(
              'inline-flex items-center gap-1 rounded-md px-2 py-1 text-xs text-muted-foreground hover:text-foreground hover:bg-muted/40 transition-colors',
            )}
          >
            <HugeiconsIcon
              icon={copied ? CheckmarkCircle01Icon : Copy01Icon}
              className="size-3.5"
              strokeWidth={2}
            />
            {copied ? 'Copied' : 'Copy'}
          </button>
        )}
      </div>
      <div className="px-4 py-3">
        {text ? (
          <pre className="whitespace-pre-wrap text-[12px] text-foreground leading-relaxed font-sans">
            {text}
          </pre>
        ) : (
          <p className="text-[12px] text-muted-foreground">
            Tidak ada yang perlu dilaporkan saat ini.
          </p>
        )}
      </div>
    </div>
  )
}

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

  // Build a readable label for each consolidated output key.
  // Keys can be: customer_id (bundled/all), account.display_name (arbel), or account.id (single).
  const allResultsList = data.results
  const customerLabel = (key: string, output?: string): string => {
    const byCustomerMap = data.customer_labels?.[key]
    if (byCustomerMap) return byCustomerMap

    if (typeof output === 'string' && output) {
      const m = output.match(/DAILY MONITORING REPORT\s*-\s*(.+?)\s+GROUP/i)
      if (m?.[1]) return m[1].trim()
    }
    // Direct customer match
    if (grouped.has(key)) {
      const results = grouped.get(key)!
      // Find the actual customer display name from results if possible
      // (results don't carry customer display_name directly, so just return the key
      //  unless it looks like a UUID — in which case try to find a display_name match)
      const uuidLike = /^[0-9a-f-]{20,}$/i.test(key)
      if (!uuidLike) return key // already a readable name
      // UUID key: find a result whose account display_name we can use as hint
      return `Customer ${key.slice(0, 8)}`
    }
    // Account display_name key (arbel mode) — check if any result has this display_name
    const byName = allResultsList.find((r) => r.account.display_name === key)
    if (byName) return byName.account.display_name
    // Account id key (single mode)
    const byId = allResultsList.find((r) => r.account.id === key)
    if (byId) return byId.account.display_name
    return key
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

      {/* Pelaporan — only for specific (single) check mode */}
      {data.mode === 'single' && <PelaporanSection results={data.results} />}

      {/* Consolidated outputs (for bundled/arbel modes) */}
      {Object.keys(data.consolidated_outputs).length > 0 && (
        <div className="space-y-3">
          <p className="text-xs font-medium text-muted-foreground">Consolidated Reports</p>
          {Object.entries(data.consolidated_outputs).map(([customerId, output]) => (
            <details key={customerId} className="rounded-lg border border-border">
              <summary className="flex items-center justify-between px-4 py-2 cursor-pointer hover:bg-muted/20 transition-colors list-none">
                <span className="text-sm font-medium">Report — {customerLabel(customerId, output)}</span>
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
