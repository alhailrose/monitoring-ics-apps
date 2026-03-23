import { getToken } from '@/lib/server-token'
import { getCustomers } from '@/lib/api/customers'
import { PageHeader } from '@/components/common/PageHeader'
import { SpecificCheckForm } from '@/components/checks/SpecificCheckForm'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { HugeiconsIcon } from '@hugeicons/react'
import {
  SearchList01Icon,
  UserAccountIcon,
  CheckmarkCircle01Icon,
  Alert01Icon,
} from '@hugeicons/core-free-icons'

const FEATURES = [
  { icon: SearchList01Icon, text: 'Pick one check type to run' },
  { icon: UserAccountIcon, text: 'Select one or more customers' },
  { icon: CheckmarkCircle01Icon, text: 'Optionally narrow to specific accounts' },
  { icon: Alert01Icon, text: 'See per-account status and findings inline' },
]

export default async function SpecificChecksPage() {
  const token = await getToken()
  const customersRaw = await getCustomers(token).catch(() => [])
  const customers = Array.isArray(customersRaw) ? customersRaw : []

  return (
    <div className="space-y-6 p-6">
      <PageHeader
        title="Specific Check"
        description="Run a targeted check against selected customers and accounts"
      />

      <div className="grid gap-6 lg:grid-cols-[280px_1fr]">
        {/* Info panel */}
        <div className="space-y-4">
          <Card className="border-border/60">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm">How it works</CardTitle>
              <CardDescription className="text-xs">
                Run one check type across multiple customers at once. Results show per-account status with full detail.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-2.5">
              {FEATURES.map((f, i) => (
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

        {/* Form card */}
        <Card>
          <CardHeader className="pb-4">
            <CardTitle className="text-base">Configure & Run</CardTitle>
            <CardDescription>
              Select a check, choose your customers, then hit Run.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <SpecificCheckForm customers={customers} />
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
