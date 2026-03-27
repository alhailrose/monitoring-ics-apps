'use client'

import { useRouter, useSearchParams, usePathname } from 'next/navigation'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import type { Customer } from '@/lib/types/api'

const ALL_VALUE = '__all__'

interface CustomerSelectorProps {
  customers: Customer[]
  customerId: string
  allowAll?: boolean
}

export function CustomerSelector({ customers, customerId, allowAll = false }: CustomerSelectorProps) {
  const router = useRouter()
  const searchParams = useSearchParams()
  const pathname = usePathname()

  const handleChange = (value: string) => {
    const params = new URLSearchParams(searchParams.toString())
    if (value === ALL_VALUE) {
      params.delete('customer_id')
    } else {
      params.set('customer_id', value)
    }
    // Reset check/filter params when switching customer — stale filters from
    // a different customer's context cause empty results and broken dropdowns
    params.delete('check_name')
    params.delete('metric_status')
    params.delete('severity')
    params.delete('page')
    const qs = params.toString()
    router.push(qs ? `${pathname}?${qs}` : pathname)
  }

  const value = customerId || (allowAll ? ALL_VALUE : '')

  return (
    <Select value={value} onValueChange={handleChange}>
      <SelectTrigger className="w-48">
        <SelectValue placeholder="Select customer" />
      </SelectTrigger>
      <SelectContent>
        {allowAll && (
          <SelectItem value={ALL_VALUE}>All Customers</SelectItem>
        )}
        {customers.map((c) => (
          <SelectItem key={c.id} value={c.id}>
            {c.display_name}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  )
}
