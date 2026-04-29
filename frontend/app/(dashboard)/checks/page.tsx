import { getToken } from '@/lib/server-token'
import { getCustomers } from '@/lib/api/customers'
import { PageHeader } from '@/components/common/PageHeader'
import { ChecksTabsHydrated } from '@/components/checks/ChecksTabsHydrated'
import { Badge } from '@/components/ui/badge'

export default async function ChecksPage() {
  const token = await getToken()
  const customersRaw = await getCustomers(token).catch(() => [])
  const customers = Array.isArray(customersRaw) ? customersRaw : []
  const envName = (process.env.NEXT_PUBLIC_APP_ENV ?? process.env.NODE_ENV ?? 'development').toUpperCase()
  const isProd = envName === 'PRODUCTION' || envName === 'PROD'

  return (
    <div className="space-y-6 p-6">
      <PageHeader
        title="Checks"
        description="Run specific, bundled, or dedicated checks across your customers"
        actions={
          <Badge className={isProd ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' : 'bg-amber-500/10 text-amber-300 border-amber-500/20'}>
            {isProd ? 'PROD' : 'DEV'}
          </Badge>
        }
      />
      <ChecksTabsHydrated customers={customers} />
    </div>
  )
}
