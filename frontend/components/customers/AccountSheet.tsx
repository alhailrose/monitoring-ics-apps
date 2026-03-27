'use client'

import { useState, useEffect, useTransition, useRef, useCallback } from 'react'
import { toast } from 'sonner'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { addAccount, updateAccount } from '@/app/(dashboard)/customers/actions'
import { HugeiconsIcon } from '@hugeicons/react'
import { Add01Icon, Delete01Icon, Loading03Icon, Tick01Icon, Alert01Icon, InformationCircleIcon, Search01Icon } from '@hugeicons/core-free-icons'
import type { Account, AuthMethod } from '@/lib/types/api'

type AuthHint = {
  intro: string
  steps: string[]
  policies?: string[]
  note?: string
  warning?: string
}

const AUTH_METHOD_HINTS: Record<AuthMethod, AuthHint> = {
  profile: {
    intro: 'Uses a named AWS profile stored on the server in ~/.aws/config or ~/.aws/credentials.',
    steps: [
      'Ensure the profile exists on the server running this app (not just your local machine).',
      'Profile name must match exactly (case-sensitive).',
      'The profile must be pre-authenticated — either via aws sso login or by having valid keys in the credentials file.',
    ],
    warning:
      'If a same-named profile exists locally AND in the app with a different auth type, credentials may leak across. Use a distinct profile name or switch to Access Key to avoid this conflict.',
  },
  access_key: {
    intro: 'Authenticates with a long-term IAM Access Key ID and Secret from a dedicated IAM user.',
    steps: [
      'In AWS Console → IAM → Users, open or create a dedicated monitoring IAM user.',
      'Go to the Security credentials tab → Access keys → Create access key.',
      'Select "Other" as the use case, complete the wizard, and save the .csv file.',
      'Copy the Access Key ID (starts with AKIA…) and Secret Access Key into the fields below.',
      'Set Region to the account\'s primary region (e.g. ap-southeast-1). Opt-in regions like Jakarta (ap-southeast-3) require explicit enablement.',
    ],
    policies: [
      'ReadOnlyAccess  — or attach individual policies: CloudWatchReadOnlyAccess, AWSHealthFullAccess, GuardDutyReadOnlyAccess, AmazonEC2ReadOnlyAccess, AWSBackupOperatorAccess, ViewOnlyAccess',
    ],
    note: 'Only one active secret key exists per IAM user at a time. Save it immediately — it cannot be retrieved after creation.',
    warning:
      'Never use root account credentials. Create a dedicated IAM user with least-privilege read-only policies.',
  },
  assumed_role: {
    intro: 'The monitoring server assumes a role in the customer account using its EC2 Instance Profile — no access key required. Each customer creates one read-only IAM Role and shares the ARN.',
    steps: [
      'Ask the monitoring app admin for the Instance Profile ARN (format: arn:aws:iam::<monitoring-account-id>:role/ics-ms-monitoring-app-role).',
      'In the CUSTOMER\'s AWS Console → IAM → Roles → Create role → select "Another AWS account" → enter the monitoring account ID.',
      'Paste the trust policy below, replacing <monitoring-account-id> with the actual value.',
      'Attach the required read-only permission policies to the role (see below).',
      'Copy the Role ARN (arn:aws:iam::<customer-account-id>:role/<role-name>) and paste it in the Role ARN field.',
      '(Optional) Set an ExternalId in the trust policy for extra security and enter the same value in the External ID field.',
    ],
    policies: [
      'TRUST POLICY (in customer account):',
      '{ "Version": "2012-10-17", "Statement": [{ "Effect": "Allow", "Principal": { "AWS": "arn:aws:iam::<monitoring-account-id>:role/ics-ms-monitoring-app-role" }, "Action": "sts:AssumeRole" }] }',
      '',
      'PERMISSION POLICY (attach to the role):',
      'cloudwatch:GetMetricStatistics, GetMetricData, DescribeAlarms, ListMetrics',
      'ec2:DescribeInstances, DescribeRegions, DescribeInstanceStatus',
      'rds:DescribeDBClusters, DescribeDBInstances',
      'guardduty:ListDetectors, GetDetector, ListFindings, GetFindings',
      'ce:GetCostAndUsage, GetAnomalies, GetAnomalyMonitors',
      'budgets:ViewBudget, DescribeBudget',
      'health:DescribeEvents, DescribeEventDetails, DescribeAffectedEntities',
      'backup:ListBackupJobs, DescribeBackupJob',
      'sts:GetCallerIdentity',
    ],
    note: 'Access Key fields are optional — leave blank to use Instance Profile. Fill them only if you need a specific base identity for the STS call.',
  },
}

interface AccountSheetProps {
  customerId: string
  account?: Account
  open: boolean
  onClose: () => void
}

export function AccountSheet({ customerId, account, open, onClose }: AccountSheetProps) {
  const isEdit = !!account
  const [isPending, startTransition] = useTransition()

  // Auth method state — synced whenever the account prop changes (e.g. after save + revalidate)
  const [authMethod, setAuthMethod] = useState<AuthMethod>(account?.auth_method ?? 'profile')
  useEffect(() => {
    setAuthMethod(account?.auth_method ?? 'profile')
    setTestResult(null)
  }, [account?.id, account?.auth_method])

  const [isTesting, setIsTesting] = useState(false)
  const [testResult, setTestResult] = useState<{ ok: boolean; message: string } | null>(null)

  // Alarm names state
  const [alarmNames, setAlarmNames] = useState<string[]>(account?.alarm_names ?? [])
  useEffect(() => {
    setAlarmNames(account?.alarm_names ?? [])
  }, [account?.id])
  const [newAlarm, setNewAlarm] = useState('')
  const [isDiscovering, setIsDiscovering] = useState(false)
  const [discoverResult, setDiscoverResult] = useState<{
    aws_account_id: string | null
    alarm_names: string[]
    ec2_instances: Array<{ instance_id: string; name: string; instance_type: string; region: string; platform: string }>
    rds_clusters: Array<{ cluster_id: string | null; engine: string | null; status: string | null }>
    rds_instances: Array<{ instance_id: string | null; engine: string | null; instance_class: string | null; status: string | null; cluster_id: string | null }>
    errors: string[]
  } | null>(null)
  useEffect(() => {
    setDiscoverResult(null)
  }, [account?.id])
  const alarmInputRef = useRef<HTMLInputElement>(null)

  const addAlarm = () => {
    const name = newAlarm.trim()
    if (!name || alarmNames.includes(name)) return
    setAlarmNames((prev) => [...prev, name].sort())
    setNewAlarm('')
    alarmInputRef.current?.focus()
  }

  const removeAlarm = (name: string) => {
    setAlarmNames((prev) => prev.filter((a) => a !== name))
  }

  const testConnection = async () => {
    if (!account?.id) return
    setIsTesting(true)
    setTestResult(null)
    try {
      const res = await fetch(`/api/test-connection/${account.id}`, { method: 'POST' })
      const data = await res.json()
      if (data.ok) {
        setTestResult({ ok: true, message: `Connected — AWS account ${data.account_id}` })
      } else {
        setTestResult({ ok: false, message: data.error ?? 'Connection failed' })
      }
    } catch {
      setTestResult({ ok: false, message: 'Request failed' })
    } finally {
      setIsTesting(false)
    }
  }

  const runFullDiscovery = useCallback(async (accountId: string) => {
    setIsDiscovering(true)
    setDiscoverResult(null)
    try {
      const res = await fetch(`/api/discover-full/${accountId}`, { method: 'POST' })
      if (!res.ok) {
        const err = await res.json().catch(() => ({}))
        toast.error('Discovery failed', { description: err.detail ?? err.error })
        return
      }
      const data = await res.json()
      setAlarmNames(data.alarm_names ?? [])
      setDiscoverResult(data)
      const parts: string[] = []
      if (data.aws_account_id) parts.push(`Account ID: ${data.aws_account_id}`)
      parts.push(`${(data.alarm_names ?? []).length} alarms`)
      if ((data.ec2_instances ?? []).length > 0) parts.push(`${data.ec2_instances.length} EC2`)
      if ((data.rds_clusters ?? []).length > 0) parts.push(`${data.rds_clusters.length} RDS cluster${data.rds_clusters.length !== 1 ? 's' : ''}`)
      if ((data.rds_instances ?? []).length > 0) parts.push(`${data.rds_instances.length} RDS instance${data.rds_instances.length !== 1 ? 's' : ''}`)
      toast.success('Discovery complete', { description: parts.join(' · ') })
    } catch {
      toast.error('Discovery failed')
    } finally {
      setIsDiscovering(false)
    }
  }, [])

  const discoverAlarms = async () => {
    if (!account?.id) return
    await runFullDiscovery(account.id)
  }

  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    const formData = new FormData(e.currentTarget)
    // Inject alarm_names as newline-joined string (actions.ts splits it back)
    formData.set('alarm_names', alarmNames.join('\n'))
    formData.set('auth_method', authMethod)
    startTransition(async () => {
      const res = isEdit
        ? await updateAccount(customerId, account.id, formData)
        : await addAccount(customerId, formData)
      if (res.error) {
        toast.error(isEdit ? 'Failed to update account' : 'Failed to add account', {
          description: res.error,
        })
      } else {
        if (!isEdit && res.id) {
          toast.success('Account added — running discovery…')
          await runFullDiscovery(res.id)
        } else {
          toast.success(isEdit ? 'Account updated' : 'Account added')
        }
        onClose()
      }
    })
  }

  return (
    <Dialog open={open} onOpenChange={(v) => !v && onClose()}>
      <DialogContent className="sm:max-w-md max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{isEdit ? 'Edit Account' : 'Add Account'}</DialogTitle>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4 py-1">
          <div className="space-y-1.5">
            <Label htmlFor="profile_name">Profile name</Label>
            <Input
              id="profile_name"
              name="profile_name"
              required
              disabled={isEdit}
              defaultValue={account?.profile_name ?? ''}
              placeholder="e.g. prod-account"
            />
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="display_name">Display name</Label>
            <Input
              id="display_name"
              name="display_name"
              required
              defaultValue={account?.display_name ?? ''}
              placeholder="e.g. Production"
            />
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="region">
              Region <span className="text-muted-foreground text-xs">(optional, e.g. ap-southeast-1)</span>
            </Label>
            <Input
              id="region"
              name="region"
              defaultValue={account?.region ?? ''}
              placeholder="ap-southeast-1"
            />
          </div>

          <div className="flex items-center gap-3">
            <input
              type="checkbox"
              id="is_active"
              name="is_active"
              defaultChecked={account?.is_active ?? true}
              className="h-4 w-4 rounded border-border accent-primary"
            />
            <Label htmlFor="is_active">Active</Label>
          </div>

          <Separator />

          {/* Auth method */}
          <div className="space-y-3">
            <div className="space-y-1.5">
              <Label>Auth method</Label>
              <Select value={authMethod} onValueChange={(v) => { setAuthMethod(v as AuthMethod); setTestResult(null) }}>
                <SelectTrigger className="h-9 text-sm">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="profile">AWS Profile (local ~/.aws)</SelectItem>
                  <SelectItem value="access_key">Access Key</SelectItem>
                  <SelectItem value="assumed_role">Assumed Role</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {/* Auth method hint */}
            {(() => {
              const hint = AUTH_METHOD_HINTS[authMethod]
              return (
                <div className="rounded-md border border-border/50 bg-muted/30 px-3 py-2.5 space-y-2 text-[11px] leading-snug">
                  {/* Intro */}
                  <p className="flex items-start gap-1.5 text-muted-foreground">
                    <HugeiconsIcon icon={InformationCircleIcon} strokeWidth={2} className="size-3.5 shrink-0 mt-px text-blue-400/70" />
                    {hint.intro}
                  </p>

                  {/* Steps */}
                  <ol className="space-y-1 pl-1">
                    {hint.steps.map((step, i) => (
                      <li key={i} className="flex items-start gap-2 text-muted-foreground">
                        <span className="shrink-0 font-mono text-[10px] text-muted-foreground/50 w-3.5 text-right mt-px">{i + 1}.</span>
                        <span>{step}</span>
                      </li>
                    ))}
                  </ol>

                  {/* Required policies */}
                  {hint.policies && (
                    <div className="space-y-1 border-t border-border/40 pt-2">
                      <p className="text-muted-foreground/60 uppercase tracking-wider text-[10px] font-medium">Required IAM policies</p>
                      {hint.policies.map((p, i) => (
                        <p key={i} className="text-muted-foreground font-mono text-[10px] break-all">{p}</p>
                      ))}
                    </div>
                  )}

                  {/* Note */}
                  {hint.note && (
                    <p className="text-muted-foreground/60 italic">{hint.note}</p>
                  )}

                  {/* Warning */}
                  {hint.warning && (
                    <p className="flex items-start gap-1.5 text-amber-400/80 pt-1 border-t border-border/40">
                      <HugeiconsIcon icon={Alert01Icon} strokeWidth={2} className="size-3.5 shrink-0 mt-px" />
                      {hint.warning}
                    </p>
                  )}
                </div>
              )
            })()}

            {(authMethod === 'access_key' || authMethod === 'assumed_role') && (
              <>
                <div className="space-y-1.5">
                  <Label htmlFor="aws_access_key_id">
                    AWS Access Key ID
                    {authMethod === 'assumed_role' && (
                      <span className="ml-1.5 text-xs font-normal text-muted-foreground">(optional — leave blank to use Instance Profile)</span>
                    )}
                  </Label>
                  <Input
                    id="aws_access_key_id"
                    name="aws_access_key_id"
                    defaultValue={account?.aws_access_key_id ?? ''}
                    placeholder="AKIA…"
                    className="font-mono text-xs"
                  />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="aws_secret_access_key">
                    AWS Secret Access Key
                    {isEdit && (
                      <span className="ml-1.5 text-xs font-normal text-muted-foreground">
                        (leave blank to keep existing)
                      </span>
                    )}
                  </Label>
                  <Input
                    id="aws_secret_access_key"
                    name="aws_secret_access_key"
                    type="password"
                    placeholder={isEdit ? '••••••••' : 'wJalrX…'}
                    className="font-mono text-xs"
                  />
                </div>
              </>
            )}

            {authMethod === 'assumed_role' && (
              <>
                <div className="space-y-1.5">
                  <Label htmlFor="role_arn">Role ARN</Label>
                  <Input
                    id="role_arn"
                    name="role_arn"
                    defaultValue={account?.role_arn ?? ''}
                    placeholder="arn:aws:iam::123456789012:role/MonitoringRole"
                    className="font-mono text-xs"
                  />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="external_id">
                    External ID
                    <span className="ml-1.5 text-xs font-normal text-muted-foreground">(optional)</span>
                  </Label>
                  <Input
                    id="external_id"
                    name="external_id"
                    defaultValue={account?.external_id ?? ''}
                    placeholder="optional external ID"
                    className="font-mono text-xs"
                  />
                </div>
              </>
            )}

            {/* Test connection — only visible when editing a non-profile account */}
            {isEdit && authMethod !== 'profile' && (
              <div className="space-y-1.5">
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  className="h-8 text-xs gap-1.5"
                  onClick={testConnection}
                  disabled={isTesting}
                >
                  {isTesting ? (
                    <HugeiconsIcon icon={Loading03Icon} className="size-3.5 animate-spin" strokeWidth={2} />
                  ) : null}
                  {isTesting ? 'Testing…' : 'Test Connection'}
                </Button>
                {testResult && (
                  <p className={`flex items-center gap-1.5 text-xs ${testResult.ok ? 'text-emerald-400' : 'text-destructive'}`}>
                    <HugeiconsIcon
                      icon={testResult.ok ? Tick01Icon : Alert01Icon}
                      strokeWidth={2}
                      className="size-3.5 shrink-0"
                    />
                    {testResult.message}
                  </p>
                )}
              </div>
            )}
          </div>

          <Separator />

          {/* Alarm names */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <Label>
                Alarm Names
                <span className="ml-1.5 text-xs font-normal text-muted-foreground">
                  (for CloudWatch alarm verification)
                </span>
              </Label>
              {isEdit && (
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  className="h-6 text-[11px] px-2 gap-1"
                  onClick={discoverAlarms}
                  disabled={isDiscovering}
                >
                  {isDiscovering ? (
                    <HugeiconsIcon icon={Loading03Icon} className="size-3 animate-spin" strokeWidth={2} />
                  ) : (
                    <HugeiconsIcon icon={Search01Icon} className="size-3" strokeWidth={2} />
                  )}
                  {isDiscovering ? 'Discovering…' : 'Discover All'}
                </Button>
              )}
            </div>

            {/* Current alarm badges */}
            {alarmNames.length > 0 && (
              <div className="flex flex-wrap gap-1.5 p-2 rounded-md border border-border/60 bg-muted/20 max-h-36 overflow-y-auto">
                {alarmNames.map((name) => (
                  <Badge
                    key={name}
                    variant="outline"
                    className="text-[10px] font-mono px-1.5 py-px h-auto gap-1 cursor-pointer hover:border-destructive/50 hover:text-destructive group"
                    onClick={() => removeAlarm(name)}
                    title="Click to remove"
                  >
                    {name}
                    <HugeiconsIcon
                      icon={Delete01Icon}
                      strokeWidth={2}
                      className="size-2.5 opacity-0 group-hover:opacity-100 transition-opacity"
                    />
                  </Badge>
                ))}
              </div>
            )}

            {alarmNames.length === 0 && (
              <p className="text-xs text-muted-foreground px-1">
                No alarm names configured.{isEdit ? ' Use Discover All or add manually.' : ' Discovery runs automatically after saving.'}
              </p>
            )}

            {/* Add alarm input */}
            <div className="flex gap-2">
              <Input
                ref={alarmInputRef}
                value={newAlarm}
                onChange={(e) => setNewAlarm(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') { e.preventDefault(); addAlarm() }
                }}
                placeholder="Alarm name (Enter to add)"
                className="h-8 text-xs font-mono"
              />
              <Button
                type="button"
                variant="outline"
                size="sm"
                className="h-8 shrink-0"
                onClick={addAlarm}
                disabled={!newAlarm.trim()}
              >
                <HugeiconsIcon icon={Add01Icon} strokeWidth={2} className="size-3.5" />
              </Button>
            </div>
          </div>

          {discoverResult && (
            <div className="rounded-md border border-border/50 bg-muted/20 p-3 space-y-2">
              <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Discovery Results</p>

              {discoverResult.aws_account_id && (
                <div className="flex items-center gap-2 text-xs">
                  <span className="text-muted-foreground shrink-0">AWS Account ID</span>
                  <span className="font-mono text-foreground">{discoverResult.aws_account_id}</span>
                </div>
              )}

              {(discoverResult.ec2_instances ?? []).length > 0 && (
                <div className="space-y-1">
                  <p className="text-xs text-muted-foreground">{discoverResult.ec2_instances.length} EC2 instance{discoverResult.ec2_instances.length !== 1 ? 's' : ''} running</p>
                  <div className="max-h-32 overflow-y-auto space-y-0.5">
                    {discoverResult.ec2_instances.map((inst) => (
                      <div key={inst.instance_id} className="flex items-center gap-2 text-[11px] font-mono text-muted-foreground">
                        <span className="shrink-0 text-muted-foreground/50">{inst.instance_id}</span>
                        <span className="truncate">{inst.name}</span>
                        <span className="shrink-0 text-muted-foreground/40">{inst.instance_type}</span>
                        <span className="shrink-0 text-muted-foreground/40">{inst.platform}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {((discoverResult.rds_clusters ?? []).length > 0 || (discoverResult.rds_instances ?? []).length > 0) && (
                <div className="space-y-1">
                  {(discoverResult.rds_clusters ?? []).length > 0 && (
                    <>
                      <p className="text-xs text-muted-foreground">{discoverResult.rds_clusters.length} RDS cluster{discoverResult.rds_clusters.length !== 1 ? 's' : ''}</p>
                      <div className="space-y-0.5">
                        {discoverResult.rds_clusters.map((c, i) => (
                          <div key={i} className="text-[11px] font-mono text-muted-foreground">
                            {c.cluster_id} <span className="text-muted-foreground/40">{c.engine} · {c.status}</span>
                          </div>
                        ))}
                      </div>
                    </>
                  )}
                  {(discoverResult.rds_instances ?? []).length > 0 && (
                    <>
                      <p className="text-xs text-muted-foreground">{discoverResult.rds_instances.length} RDS instance{discoverResult.rds_instances.length !== 1 ? 's' : ''}</p>
                      <div className="space-y-0.5">
                        {discoverResult.rds_instances.map((r, i) => (
                          <div key={i} className="text-[11px] font-mono text-muted-foreground">
                            {r.instance_id} <span className="text-muted-foreground/40">{r.engine} · {r.instance_class} · {r.status}</span>
                          </div>
                        ))}
                      </div>
                    </>
                  )}
                </div>
              )}

              {(discoverResult.errors ?? []).length > 0 && (
                <div className="space-y-0.5">
                  {discoverResult.errors.map((err, i) => (
                    <p key={i} className="text-[11px] text-amber-400/70">{err}</p>
                  ))}
                </div>
              )}
            </div>
          )}

          <DialogFooter className="pt-2">
            <Button type="button" variant="outline" onClick={onClose} disabled={isPending}>
              Cancel
            </Button>
            <Button type="submit" disabled={isPending}>
              {isPending ? 'Saving…' : isEdit ? 'Save changes' : 'Add account'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
