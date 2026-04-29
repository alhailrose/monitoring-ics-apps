import { getToken } from '@/lib/server-token'
import { getCustomers } from '@/lib/api/customers'
import { PageHeader } from '@/components/common/PageHeader'
import { ChecksTabsHydrated } from '@/components/checks/ChecksTabsHydrated'

export default async function ChecksPage() {
  const token = await getToken()
  const customersRaw = await getCustomers(token).catch(() => [])
  const customers = Array.isArray(customersRaw) ? customersRaw : []

  return (
    <div className="space-y-6 p-6">
      <PageHeader
        title="Checks"
        description="Run specific, bundled, or dedicated checks across your customers"
      />
      <ChecksTabsHydrated customers={customers} />
    </div>
  )
}
