import { getSession } from '@/lib/auth'
import { getToken } from '@/lib/server-token'
import { getCustomers } from '@/lib/api/customers'
import { PageHeader } from '@/components/common/PageHeader'
import { CustomerList } from '@/components/customers/CustomerList'

export default async function CustomersPage() {
  const [session, token] = await Promise.all([getSession(), getToken()])
  const role = session?.role ?? 'user'
  const customers = await getCustomers(token).catch(() => [])

  return (
    <div className="space-y-6 p-6">
      <PageHeader
        title="Customers"
        description="Manage customers, accounts, and their AWS credentials"
      />
      <CustomerList customers={customers} role={role} />
    </div>
  )
}
