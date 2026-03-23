import { getToken } from '@/lib/server-token'
import { getCustomers } from '@/lib/api/customers'
import { PageHeader } from '@/components/common/PageHeader'
import { BundledCheckForm } from '@/components/checks/BundledCheckForm'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { HugeiconsIcon } from '@hugeicons/react'
import {
  CheckListIcon,
  Copy01Icon,
  UserAccountIcon,
  DocumentAttachmentIcon,
} from '@hugeicons/core-free-icons'

const FEATURES = [
  { icon: CheckListIcon, text: 'All Checks — runs every configured check for each customer' },
  { icon: DocumentAttachmentIcon, text: 'Arbel Suite — daily reporting bundle (utilization + budget + alarms)' },
  { icon: UserAccountIcon, text: 'Multi-customer — run across all customers in one go' },
  { icon: Copy01Icon, text: 'Copy report per customer directly to clipboard' },
]

export default async function BundledChecksPage() {
  const token = await getToken()
  const customersRaw = await getCustomers(token).catch(() => [])
  const customers = Array.isArray(customersRaw) ? customersRaw : []

  return (
    <div className="space-y-6 p-6">
      <PageHeader
        title="Bundled Check"
        description="Run all checks or the Arbel suite across multiple customers and get formatted reports"
      />

      <div className="grid gap-6 lg:grid-cols-[280px_1fr]">
        {/* Info panel */}
        <div className="space-y-4">
          <Card className="border-border/60">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm">How it works</CardTitle>
              <CardDescription className="text-xs">
                Bundled checks are designed for daily reporting. Each customer gets its own collapsible report card with a one-click copy button.
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

          <Card className="border-yellow-500/30 bg-yellow-500/5">
            <CardContent className="pt-4 pb-3">
              <p className="text-[11px] text-yellow-400/80 leading-relaxed">
                Bundled checks may take longer to complete depending on the number of customers and accounts.
              </p>
            </CardContent>
          </Card>
        </div>

        {/* Form card */}
        <Card>
          <CardHeader className="pb-4">
            <CardTitle className="text-base">Configure & Run</CardTitle>
            <CardDescription>
              Choose a mode, select customers, then run. Reports appear per customer below.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <BundledCheckForm customers={customers} />
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
