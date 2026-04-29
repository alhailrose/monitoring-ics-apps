import { notFound } from 'next/navigation'
import Link from 'next/link'
import { getSession } from '@/lib/auth'
import { getToken } from '@/lib/server-token'
import { getCustomer } from '@/lib/api/customers'
import { getFindings } from '@/lib/api/findings'
import { getHistory } from '@/lib/api/history'
import { PageHeader } from '@/components/common/PageHeader'
import { CustomerDetailView } from '@/components/customers/CustomerDetailView'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { HugeiconsIcon } from '@hugeicons/react'
import { ArrowLeft01Icon } from '@hugeicons/core-free-icons'

const FINDINGS_LIMIT = 20
const HISTORY_LIMIT = 15

export default async function CustomerDetailPage({
  params,
}: {
  params: Promise<{ id: string }>
}) {
  const { id } = await params
  const [session, token] = await Promise.all([getSession(), getToken()])
  const role = session?.role ?? 'user'

  const [customer, findingsData, historyData] = await Promise.all([
    getCustomer(id, token).catch(() => null),
    getFindings({ customer_id: id, status: 'active', limit: FINDINGS_LIMIT }, token).catch(
      () => ({ items: [], total: 0 }),
    ),
    getHistory({ customer_id: id, limit: HISTORY_LIMIT }, token).catch(
      () => ({ items: [], total: 0 }),
    ),
  ])

  if (!customer) notFound()

  const reportModeBadge = {
    simple: 'bg-sky-500/10 text-sky-400 border-sky-500/20',
    summary: 'bg-violet-500/10 text-violet-400 border-violet-500/20',
    detailed: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
  }[customer.report_mode] ?? 'bg-muted text-muted-foreground border-border/50'

  return (
    <div className="space-y-6 p-6">
      {/* Back */}
      <Button variant="ghost" size="sm" asChild className="-ml-2">
        <Link href="/customers">
          <HugeiconsIcon icon={ArrowLeft01Icon} strokeWidth={2} className="size-4 mr-1" />
          Customers
        </Link>
      </Button>

      {/* Header */}
      <div className="flex items-start gap-3">
        <div className="flex-1">
          <PageHeader
            title={customer.display_name}
            description={
              customer.label
                ? `${customer.label} · ${customer.name}`
                : customer.name
            }
            actions={
              <div className="flex items-center gap-2">
                <Badge className={reportModeBadge}>{customer.report_mode}</Badge>
                {customer.slack_enabled && (
                  <Badge className="bg-emerald-500/10 text-emerald-400 border-emerald-500/20">
                    Slack
                  </Badge>
                )}
              </div>
            }
          />
        </div>
      </div>

      {/* Detail view (client component with tabs) */}
      <CustomerDetailView
        customer={customer}
        findings={findingsData.items}
        findingsTotal={findingsData.total}
        runs={historyData.items}
        runsTotal={historyData.total}
        role={role}
      />
    </div>
  )
}
