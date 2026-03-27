'use client'
// Client component — needs tabs state

import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import { SpecificCheckForm } from '@/components/checks/SpecificCheckForm'
import { BundledCheckForm } from '@/components/checks/BundledCheckForm'
import { DedicatedCheckForm } from '@/components/checks/DedicatedCheckForm'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { HugeiconsIcon } from '@hugeicons/react'
import {
  SearchList01Icon,
  CheckListIcon,
  Chart01Icon,
  DollarCircleIcon,
  Alert01Icon,
  ComputerIcon,
  DocumentAttachmentIcon,
  UserAccountIcon,
  Copy01Icon,
  CheckmarkCircle01Icon,
  ArchiveRestoreIcon,
} from '@hugeicons/core-free-icons'
import type { Customer } from '@/lib/types/api'

const ARBEL_CHECKS = [
  { value: 'daily-arbel-rds',    label: 'RDS Utilization' },
  { value: 'daily-arbel-ec2',    label: 'EC2 Utilization' },
  { value: 'backup',             label: 'Backup' },
  { value: 'daily-budget',       label: 'Daily Budget' },
  { value: 'alarm_verification', label: 'Alarm Verification' },
]

const HUAWEI_CHECKS = [
  { value: 'huawei-ecs-util', label: 'ECS Utilization' },
]

interface ChecksTabsProps {
  customers: Customer[]
}

export function ChecksTabs({ customers }: ChecksTabsProps) {
  const arbelCustomers = customers.filter((c) => c.checks.includes('daily-arbel'))
  const huaweiCustomers = customers.filter((c) => c.checks.includes('huawei-ecs-util'))
  const arbelAccounts = arbelCustomers.flatMap((c) => c.accounts)
  const huaweiAccounts = huaweiCustomers.flatMap((c) => c.accounts)

  return (
    <Tabs defaultValue="specific" className="space-y-6">
      <TabsList className="h-10">
        <TabsTrigger value="specific">Specific</TabsTrigger>
        <TabsTrigger value="bundled">Bundled</TabsTrigger>
        <TabsTrigger value="arbel">Arbel</TabsTrigger>
        <TabsTrigger value="huawei">Huawei</TabsTrigger>
      </TabsList>

      {/* ── Specific ── */}
      <TabsContent value="specific">
        <div className="grid gap-6 lg:grid-cols-[260px_1fr]">
          <div className="space-y-3">
            <Card className="border-border/60">
              <CardHeader className="pb-3">
                <CardTitle className="text-sm">How it works</CardTitle>
                <CardDescription className="text-xs">
                  Run one check type across selected customers. Results show per-account status with full detail.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-2.5">
                {[
                  { icon: SearchList01Icon, text: 'Pick one check type to run' },
                  { icon: UserAccountIcon, text: 'Select one or more customers' },
                  { icon: CheckmarkCircle01Icon, text: 'Optionally narrow to specific accounts' },
                  { icon: Alert01Icon, text: 'See per-account status inline' },
                ].map((f, i) => (
                  <div key={i} className="flex items-start gap-2.5">
                    <div className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-md bg-primary/10">
                      <HugeiconsIcon icon={f.icon} strokeWidth={2} className="size-3 text-primary" />
                    </div>
                    <p className="text-xs text-muted-foreground leading-relaxed">{f.text}</p>
                  </div>
                ))}
              </CardContent>
            </Card>
            <Card className="border-border/60 bg-muted/30">
              <CardContent className="pt-4 pb-3">
                <p className="text-[11px] text-muted-foreground leading-relaxed">
                  Tip: Leave accounts unselected to run against all active accounts for that customer.
                </p>
              </CardContent>
            </Card>
          </div>
          <Card>
            <CardHeader className="pb-4">
              <CardTitle className="text-base">Configure & Run</CardTitle>
              <CardDescription>Select a check, choose your customers, then hit Run.</CardDescription>
            </CardHeader>
            <CardContent>
              <SpecificCheckForm customers={customers} />
            </CardContent>
          </Card>
        </div>
      </TabsContent>

      {/* ── Bundled ── */}
      <TabsContent value="bundled">
        <div className="grid gap-6 lg:grid-cols-[260px_1fr]">
          <div className="space-y-3">
            <Card className="border-border/60">
              <CardHeader className="pb-3">
                <CardTitle className="text-sm">How it works</CardTitle>
                <CardDescription className="text-xs">
                  Designed for daily reporting. Each customer gets its own collapsible report card with a one-click copy button.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-2.5">
                {[
                  { icon: CheckListIcon, text: 'All Checks — runs every configured check per customer' },
                  { icon: DocumentAttachmentIcon, text: 'Arbel Suite — daily reporting bundle' },
                  { icon: UserAccountIcon, text: 'Multi-customer — run across all at once' },
                  { icon: Copy01Icon, text: 'Copy report per customer to clipboard' },
                ].map((f, i) => (
                  <div key={i} className="flex items-start gap-2.5">
                    <div className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-md bg-primary/10">
                      <HugeiconsIcon icon={f.icon} strokeWidth={2} className="size-3 text-primary" />
                    </div>
                    <p className="text-xs text-muted-foreground leading-relaxed">{f.text}</p>
                  </div>
                ))}
              </CardContent>
            </Card>
            <Card className="border-yellow-500/30 bg-yellow-500/5">
              <CardContent className="pt-4 pb-3">
                <p className="text-[11px] text-yellow-400/80 leading-relaxed">
                  Bundled checks may take longer depending on the number of customers and accounts.
                </p>
              </CardContent>
            </Card>
          </div>
          <Card>
            <CardHeader className="pb-4">
              <CardTitle className="text-base">Configure & Run</CardTitle>
              <CardDescription>Choose a mode, select customers, then run. Reports appear per customer below.</CardDescription>
            </CardHeader>
            <CardContent>
              <BundledCheckForm customers={customers} />
            </CardContent>
          </Card>
        </div>
      </TabsContent>

      {/* ── Arbel ── */}
      <TabsContent value="arbel">
        <div className="grid gap-6 lg:grid-cols-[260px_1fr]">
          <Card className="border-border/60 h-fit">
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <CardTitle className="text-sm">Available Checks</CardTitle>
                <Badge className="text-[10px] bg-primary/10 text-primary border-primary/20">Dedicated</Badge>
              </div>
              <CardDescription className="text-xs">
                Purpose-built for Arya Noble's AWS environment.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {[
                { icon: CheckListIcon, name: 'RDS Utilization', desc: 'CPU, memory, connections for RDS clusters — detects spikes and anomalies' },
                { icon: ComputerIcon, name: 'EC2 Utilization', desc: 'CPU, NetworkIn/Out for EC2 instances — detects high utilization' },
                { icon: ArchiveRestoreIcon, name: 'Backup', desc: 'AWS Backup job status — detects failed or missed backup jobs' },
                { icon: DollarCircleIcon, name: 'Daily Budget', desc: 'AWS cost and budget monitoring — detects anomalies and overspend' },
                { icon: Alert01Icon, name: 'Alarm Verification', desc: 'Verifies CloudWatch alarms are correctly configured and firing' },
              ].map((c, i) => (
                <div key={i} className="flex items-start gap-2.5">
                  <div className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-md bg-primary/10">
                    <HugeiconsIcon icon={c.icon} strokeWidth={2} className="size-3 text-primary" />
                  </div>
                  <div>
                    <p className="text-xs font-medium text-foreground">{c.name}</p>
                    <p className="text-[11px] text-muted-foreground leading-relaxed">{c.desc}</p>
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-4">
              <CardTitle className="text-base">Run Arbel Check</CardTitle>
              <CardDescription>Select which check to run and which customers to target.</CardDescription>
            </CardHeader>
            <CardContent>
              <DedicatedCheckForm checkGroup="arbel" label="Arbel Check" accounts={arbelAccounts} customers={arbelCustomers} checkNames={ARBEL_CHECKS} />
            </CardContent>
          </Card>
        </div>
      </TabsContent>

      {/* ── Huawei ── */}
      <TabsContent value="huawei">
        <div className="grid gap-6 lg:grid-cols-[260px_1fr]">
          <Card className="border-border/60 h-fit">
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <CardTitle className="text-sm">Available Checks</CardTitle>
                <Badge className="text-[10px] bg-blue-500/10 text-blue-400 border-blue-500/20">Huawei Cloud</Badge>
              </div>
              <CardDescription className="text-xs">
                Checks specific to Huawei Cloud infrastructure.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {[
                { icon: ComputerIcon, name: 'ECS Utilization', desc: 'Monitors Huawei Cloud ECS instance CPU, memory, and disk utilization' },
                { icon: Chart01Icon, name: 'Coming soon', desc: 'Additional Huawei Cloud checks will be added as the platform expands' },
              ].map((c, i) => (
                <div key={i} className="flex items-start gap-2.5">
                  <div className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-md bg-blue-500/10">
                    <HugeiconsIcon icon={c.icon} strokeWidth={2} className="size-3 text-blue-400" />
                  </div>
                  <div>
                    <p className="text-xs font-medium text-foreground">{c.name}</p>
                    <p className="text-[11px] text-muted-foreground leading-relaxed">{c.desc}</p>
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>
          <Card>
            <CardHeader className="pb-4">
              <CardTitle className="text-base">Run Huawei Check</CardTitle>
              <CardDescription>Select customers with Huawei Cloud accounts to monitor.</CardDescription>
            </CardHeader>
            <CardContent>
              <DedicatedCheckForm checkGroup="huawei" label="Huawei Check" accounts={huaweiAccounts} customers={huaweiCustomers} checkNames={HUAWEI_CHECKS} />
            </CardContent>
          </Card>
        </div>
      </TabsContent>
    </Tabs>
  )
}
