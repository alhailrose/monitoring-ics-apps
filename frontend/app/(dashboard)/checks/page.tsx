import { getToken } from '@/lib/server-token'
import { getCustomers } from '@/lib/api/customers'
import { PageHeader } from '@/components/common/PageHeader'
import { ChecksTabs } from '@/components/checks/ChecksTabs'

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
      <ChecksTabs customers={customers} />
    </div>
  )
}
