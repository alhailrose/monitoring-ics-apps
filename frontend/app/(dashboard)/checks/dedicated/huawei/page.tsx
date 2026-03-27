import { getToken } from '@/lib/server-token'
import { getCustomers } from '@/lib/api/customers'
import { PageHeader } from '@/components/common/PageHeader'
import { DedicatedCheckForm } from '@/components/checks/DedicatedCheckForm'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { HugeiconsIcon } from '@hugeicons/react'
import { Chart01Icon, ComputerIcon } from '@hugeicons/core-free-icons'

const HUAWEI_CHECKS = [
  { value: 'huawei-ecs-util', label: 'ECS Utilization' },
]

const CHECK_INFO = [
  {
    icon: ComputerIcon,
    name: 'ECS Utilization',
    desc: 'Monitors Huawei Cloud ECS instance CPU, memory, and disk utilization',
  },
  {
    icon: Chart01Icon,
    name: 'Coming soon',
    desc: 'Additional Huawei Cloud checks will be added as the platform expands',
  },
]

export default async function HuaweiCheckPage() {
  const token = await getToken()
  const customersRaw = await getCustomers(token).catch(() => [])
  const allCustomers = Array.isArray(customersRaw) ? customersRaw : []
  const huaweiCustomers = allCustomers.filter((c) => c.checks.includes('huawei-ecs-util'))
  const accounts = huaweiCustomers.flatMap((c) => c.accounts)

  return (
    <div className="space-y-6 p-6">
      <PageHeader
        title="Huawei Check"
        description="Dedicated checks for Huawei Cloud ECS instances"
      />

      <div className="grid gap-6 lg:grid-cols-[280px_1fr]">
        {/* Info panel */}
        <div className="space-y-4">
          <Card className="border-border/60">
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <CardTitle className="text-sm">Available Checks</CardTitle>
                <Badge className="text-[10px] bg-blue-500/10 text-blue-400 border-blue-500/20">
                  Huawei Cloud
                </Badge>
              </div>
              <CardDescription className="text-xs">
                Checks specific to Huawei Cloud infrastructure.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {CHECK_INFO.map((c, i) => (
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

          <Card className="border-blue-500/20 bg-blue-500/5">
            <CardContent className="pt-4 pb-3">
              <p className="text-[11px] text-blue-400/80 leading-relaxed">
                Huawei Cloud checks use a separate credential path. Ensure Huawei profiles are configured before running.
              </p>
            </CardContent>
          </Card>
        </div>

        {/* Form card */}
        <Card>
          <CardHeader className="pb-4">
            <CardTitle className="text-base">Run Huawei Check</CardTitle>
            <CardDescription>
              Select customers with Huawei Cloud accounts to monitor.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <DedicatedCheckForm
              checkGroup="huawei"
              label="Huawei Check"
              accounts={accounts}
              customers={huaweiCustomers}
              checkNames={HUAWEI_CHECKS}
            />
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
