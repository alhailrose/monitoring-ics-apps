'use client'

import { useEffect, useState } from 'react'
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from '@/components/ui/sheet'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { Separator } from '@/components/ui/separator'
import { HugeiconsIcon } from '@hugeicons/react'
import { RefreshIcon, AlertCircleIcon } from '@hugeicons/core-free-icons'
import type { Account } from '@/lib/types/api'

// ── Types ─────────────────────────────────────────────────────────────────────

interface DiscoveryResult {
  aws_account_id: string | null
  alarm_names: string[]
  ec2_instances: Array<{
    instance_id: string
    name: string
    instance_type: string
    region: string
    platform: string
  }>
  rds_clusters: Array<{
    cluster_id: string | null
    engine: string | null
    status: string | null
  }>
  rds_instances: Array<{
    instance_id: string | null
    engine: string | null
    instance_class: string | null
    status: string | null
    cluster_id: string | null
  }>
  errors: string[]
}

interface AccountDetailsSheetProps {
  account: Account | null
  open: boolean
  onClose: () => void
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function SectionHeader({ children }: { children: React.ReactNode }) {
  return (
    <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-2">
      {children}
    </p>
  )
}

function platformBadge(platform: string) {
  const lower = platform.toLowerCase()
  if (lower.includes('win')) {
    return (
      <Badge className="h-4 px-1.5 text-[10px] bg-blue-500/10 text-blue-400 border-blue-500/20">
        Windows
      </Badge>
    )
  }
  return (
    <Badge className="h-4 px-1.5 text-[10px] bg-green-500/10 text-green-400 border-green-500/20">
      Linux
    </Badge>
  )
}

function statusBadge(status: string | null) {
  if (!status) return <span className="text-xs text-muted-foreground/40">—</span>
  const lower = status.toLowerCase()
  const isOk = lower === 'available' || lower === 'running' || lower === 'active'
  return (
    <Badge
      className={
        isOk
          ? 'h-4 px-1.5 text-[10px] bg-green-500/10 text-green-400 border-green-500/20'
          : 'h-4 px-1.5 text-[10px] bg-amber-500/10 text-amber-400 border-amber-500/20'
      }
    >
      {status}
    </Badge>
  )
}

// ── Component ─────────────────────────────────────────────────────────────────

export function AccountDetailsSheet({ account, open, onClose }: AccountDetailsSheetProps) {
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState<DiscoveryResult | null>(null)
  const [snapshotAt, setSnapshotAt] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  // Load stored snapshot from DB — no AWS call
  const loadSnapshot = async () => {
    if (!account) return
    setLoading(true)
    setError(null)
    try {
      const res = await fetch(`/api/discovery-snapshot/${account.id}`)
      if (!res.ok) return
      const data = await res.json()
      if (data.snapshot) {
        const { timestamp, ...rest } = data.snapshot
        setResult(rest as DiscoveryResult)
        setSnapshotAt(timestamp ?? null)
      }
    } catch {
      // silently ignore — user can Re-discover
    } finally {
      setLoading(false)
    }
  }

  // Live fetch from AWS — updates DB and state
  const runDiscovery = async () => {
    if (!account) return
    setLoading(true)
    setError(null)
    try {
      const res = await fetch(`/api/discover-full/${account.id}`, { method: 'POST' })
      if (!res.ok) {
        const data = await res.json().catch(() => ({}))
        setError((data as { detail?: string; error?: string }).detail ?? (data as { error?: string }).error ?? 'Discovery failed')
        return
      }
      const data = await res.json()
      setResult(data)
      setSnapshotAt(new Date().toISOString())
    } catch {
      setError('Request failed')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (open && account) {
      setResult(null)
      setSnapshotAt(null)
      loadSnapshot()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, account?.id])

  return (
    <Sheet open={open} onOpenChange={(v) => !v && onClose()}>
      <SheetContent side="right" className="w-full sm:max-w-xl overflow-y-auto">
        <SheetHeader className="pr-10">
          <SheetTitle>{account?.display_name ?? 'Account Details'}</SheetTitle>
          <SheetDescription className="font-mono text-xs">
            {account?.profile_name}
            {result?.aws_account_id && ` · ${result.aws_account_id} (AWS)`}
          </SheetDescription>
        </SheetHeader>

        <div className="mt-4 space-y-5">
          {/* Re-discover button + last snapshot time */}
          <div className="flex items-center justify-between gap-3">
            {snapshotAt ? (
              <p className="text-[11px] text-muted-foreground/50">
                Last discovered:{' '}
                {new Date(snapshotAt).toLocaleString('id-ID', {
                  day: '2-digit', month: 'short', year: 'numeric',
                  hour: '2-digit', minute: '2-digit',
                })}
              </p>
            ) : (
              <span />
            )}
            <Button
              variant="outline"
              size="sm"
              className="h-7 text-xs gap-1.5 shrink-0"
              onClick={runDiscovery}
              disabled={loading}
            >
              <HugeiconsIcon
                icon={RefreshIcon}
                strokeWidth={2}
                className={`size-3.5 ${loading ? 'animate-spin' : ''}`}
              />
              {loading ? 'Discovering…' : 'Re-discover'}
            </Button>
          </div>

          {/* Error banner */}
          {error && (
            <div className="flex items-center gap-2 text-sm text-destructive">
              <HugeiconsIcon icon={AlertCircleIcon} strokeWidth={2} className="size-4 shrink-0" />
              {error}
            </div>
          )}

          {/* Loading skeletons */}
          {loading && !result && (
            <div className="space-y-3">
              <Skeleton className="h-4 w-32" />
              <Skeleton className="h-24 w-full" />
              <Skeleton className="h-4 w-24" />
              <Skeleton className="h-16 w-full" />
            </div>
          )}

          {/* Results */}
          {result && (
            <>
              {/* AWS Account */}
              <div>
                <SectionHeader>AWS Account</SectionHeader>
                <div className="rounded-md border border-border/50 bg-muted/20 px-3 py-2.5 space-y-1.5">
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-muted-foreground w-24 shrink-0">Account ID</span>
                    <span className="font-mono text-xs text-foreground">
                      {result.aws_account_id ?? account?.account_id ?? '—'}
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-muted-foreground w-24 shrink-0">Region</span>
                    <span className="font-mono text-xs text-foreground">
                      {account?.region ?? '—'}
                    </span>
                  </div>
                </div>
              </div>

              <Separator className="bg-border/40" />

              {/* EC2 Instances */}
              {result.ec2_instances.length > 0 && (
                <>
                  <div>
                    <SectionHeader>
                      EC2 Instances ({result.ec2_instances.length} running)
                    </SectionHeader>
                    <div className="rounded-md border border-border/50 overflow-hidden">
                      <div className="max-h-64 overflow-y-auto divide-y divide-border/30">
                        {result.ec2_instances.map((inst) => (
                          <div
                            key={inst.instance_id}
                            className="flex flex-wrap items-center gap-x-3 gap-y-1 px-3 py-2 hover:bg-muted/20 transition-colors"
                          >
                            <span className="font-mono text-xs text-muted-foreground shrink-0">
                              {inst.instance_id}
                            </span>
                            <span className="text-sm font-medium text-foreground truncate flex-1 min-w-0">
                              {inst.name || '—'}
                            </span>
                            <span className="font-mono text-xs text-muted-foreground/70 shrink-0">
                              {inst.instance_type}
                            </span>
                            <span className="font-mono text-xs text-muted-foreground/50 shrink-0">
                              {inst.region}
                            </span>
                            {inst.platform && platformBadge(inst.platform)}
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                  <Separator className="bg-border/40" />
                </>
              )}

              {/* RDS Clusters */}
              {result.rds_clusters.length > 0 && (
                <>
                  <div>
                    <SectionHeader>RDS Clusters ({result.rds_clusters.length})</SectionHeader>
                    <div className="rounded-md border border-border/50 overflow-hidden">
                      <div className="divide-y divide-border/30">
                        {result.rds_clusters.map((c, i) => (
                          <div
                            key={c.cluster_id ?? i}
                            className="flex flex-wrap items-center gap-x-3 gap-y-1 px-3 py-2 hover:bg-muted/20 transition-colors"
                          >
                            <span className="font-mono text-xs text-muted-foreground flex-1 min-w-0 truncate">
                              {c.cluster_id ?? '—'}
                            </span>
                            <span className="text-xs text-muted-foreground/70 shrink-0">
                              {c.engine ?? '—'}
                            </span>
                            {statusBadge(c.status)}
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                  <Separator className="bg-border/40" />
                </>
              )}

              {/* RDS Instances */}
              {result.rds_instances.length > 0 && (
                <>
                  <div>
                    <SectionHeader>RDS Instances ({result.rds_instances.length})</SectionHeader>
                    <div className="rounded-md border border-border/50 overflow-hidden">
                      <div className="max-h-48 overflow-y-auto divide-y divide-border/30">
                        {result.rds_instances.map((inst, i) => (
                          <div
                            key={inst.instance_id ?? i}
                            className="flex flex-wrap items-center gap-x-3 gap-y-1 px-3 py-2 hover:bg-muted/20 transition-colors"
                          >
                            <span className="font-mono text-xs text-muted-foreground shrink-0">
                              {inst.instance_id ?? '—'}
                            </span>
                            <span className="text-xs text-muted-foreground/70 shrink-0">
                              {[inst.engine, inst.instance_class].filter(Boolean).join(' · ') || '—'}
                            </span>
                            {statusBadge(inst.status)}
                            {inst.cluster_id && (
                              <span className="font-mono text-xs text-muted-foreground/40 ml-auto shrink-0">
                                {inst.cluster_id}
                              </span>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                  <Separator className="bg-border/40" />
                </>
              )}

              {/* Alarms */}
              <div>
                <SectionHeader>
                  Alarms ({result.alarm_names.length} configured)
                </SectionHeader>
                {result.alarm_names.length === 0 ? (
                  <p className="text-xs text-muted-foreground/50">No alarms configured.</p>
                ) : (
                  <div className="rounded-md border border-border/50 bg-muted/20 px-3 py-2.5 space-y-1">
                    {result.alarm_names.slice(0, 5).map((name) => (
                      <p key={name} className="font-mono text-xs text-foreground/80 truncate">
                        {name}
                      </p>
                    ))}
                    {result.alarm_names.length > 5 && (
                      <p className="text-xs text-muted-foreground/50 pt-0.5">
                        + {result.alarm_names.length - 5} more
                      </p>
                    )}
                  </div>
                )}
              </div>

              {/* Errors */}
              {result.errors.length > 0 && (
                <>
                  <Separator className="bg-border/40" />
                  <div>
                    <SectionHeader>Errors</SectionHeader>
                    <div className="space-y-1.5">
                      {result.errors.map((err, i) => (
                        <div key={i} className="flex items-start gap-2">
                          <HugeiconsIcon
                            icon={AlertCircleIcon}
                            strokeWidth={2}
                            className="size-3.5 text-amber-400 shrink-0 mt-0.5"
                          />
                          <p className="text-xs text-amber-400">{err}</p>
                        </div>
                      ))}
                    </div>
                  </div>
                </>
              )}
            </>
          )}
        </div>
      </SheetContent>
    </Sheet>
  )
}
