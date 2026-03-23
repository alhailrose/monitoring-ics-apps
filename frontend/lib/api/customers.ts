import { apiFetch } from './client'
import type { Customer, Account } from '@/lib/types/api'

export async function getCustomers(token: string): Promise<Customer[]> {
  const res = await apiFetch<{ customers: Customer[] } | Customer[]>('/customers', { token })
  return Array.isArray(res) ? res : (res as { customers: Customer[] }).customers ?? []
}

export async function createCustomer(
  data: Partial<Customer>,
  token: string,
): Promise<Customer> {
  return apiFetch<Customer>('/customers', {
    method: 'POST',
    body: JSON.stringify(data),
    token,
  })
}

export async function updateCustomer(
  id: string,
  data: Partial<Customer>,
  token: string,
): Promise<Customer> {
  return apiFetch<Customer>(`/customers/${id}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
    token,
  })
}

export async function deleteCustomer(id: string, token: string): Promise<void> {
  return apiFetch<void>(`/customers/${id}`, { method: 'DELETE', token })
}

export async function createAccount(
  customerId: string,
  data: Partial<Account>,
  token: string,
): Promise<Account> {
  return apiFetch<Account>(`/customers/${customerId}/accounts`, {
    method: 'POST',
    body: JSON.stringify(data),
    token,
  })
}

export async function updateAccount(
  _customerId: string,
  accountId: string,
  data: Partial<Account>,
  token: string,
): Promise<Account> {
  return apiFetch<Account>(`/customers/accounts/${accountId}`, {
    method: 'PATCH',
    body: JSON.stringify(data),
    token,
  })
}

export async function deleteAccount(
  _customerId: string,
  accountId: string,
  token: string,
): Promise<void> {
  return apiFetch<void>(`/customers/accounts/${accountId}`, {
    method: 'DELETE',
    token,
  })
}
