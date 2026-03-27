import { getToken } from '@/lib/server-token'
import { getCustomers } from '@/lib/api/customers'
import { PageHeader } from '@/components/common/PageHeader'
import { DedicatedCheckForm } from '@/components/checks/DedicatedCheckForm'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { HugeiconsIcon } from '@hugeicons/react'
import {
  Chart01Icon,
  DollarCircleIcon,
  Alert01Icon,
  Database01Icon,
  ComputerIcon,
  ArchiveRestoreIcon,
} from '@hugeicons/core-free-icons'

const ARBEL_CHECKS = [
  { value: 'daily-arbel-rds',    label: 'RDS Utilization' },
  { value: 'daily-arbel-ec2',    label: 'EC2 Utilization' },
  { value: 'backup',             label: 'Backup' },
  { value: 'daily-budget',       label: 'Daily Budget' },
  { value: 'alarm_verification', label: 'Alarm Verification' },
]

const CHECK_INFO = [
  {
    icon: Database01Icon,
    name: 'RDS Utilization',
    desc: 'CPU, memory, connections for RDS clusters — detects spikes and anomalies',
  },
  {
    icon: ComputerIcon,
    name: 'EC2 Utilization',
    desc: 'CPU, NetworkIn/Out for EC2 instances — detects high utilization',
  },
  {
    icon: ArchiveRestoreIcon,
    name: 'Backup',
    desc: 'AWS Backup job status — detects failed or missed backup jobs',
  },
  {
    icon: Chart01Icon,
    name: 'Daily Budget',
    desc: 'Cost and budget monitoring — detects anomalies and overspend',
  },
  {
    icon: Alert01Icon,
    name: 'Alarm Verification',
    desc: 'Verifies CloudWatch alarms are correctly configured per account',
  },
]

export default async function ArbelCheckPage() {
  const token = await getToken()
  const customersRaw = await getCustomers(token).catch(() => [])
  const allCustomers = Array.isArray(customersRaw) ? customersRaw : []
  const arbelCustomers = allCustomers.filter((c) => c.checks.includes('daily-arbel'))
  const accounts = arbelCustomers.flatMap((c) => c.accounts)

  return (
    <div className="space-y-6 p-6">
      <PageHeader
        title="Arbel Check"
        description="Dedicated daily checks for Arya Noble — utilization, budget, and alarm verification"
      />

      <div className="grid gap-6 lg:grid-cols-[280px_1fr]">
        {/* Info panel */}
        <div className="space-y-4">
          <Card className="border-border/60">
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <CardTitle className="text-sm">Available Checks</CardTitle>
                <Badge className="text-[10px] bg-primary/10 text-primary border-primary/20">
                  Dedicated
                </Badge>
              </div>
              <CardDescription className="text-xs">
                Arbel checks are purpose-built for Arya Noble's AWS environment.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {CHECK_INFO.map((c, i) => (
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
        </div>

        {/* Form card */}
        <Card>
          <CardHeader className="pb-4">
            <CardTitle className="text-base">Run Arbel Check</CardTitle>
            <CardDescription>
              Select which check to run and which customers to target.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <DedicatedCheckForm
              checkGroup="arbel"
              label="Arbel Check"
              accounts={accounts}
              customers={arbelCustomers}
              checkNames={ARBEL_CHECKS}
            />
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
