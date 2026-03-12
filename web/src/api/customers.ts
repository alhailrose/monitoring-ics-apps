import { ApiError, apiRequest } from "./client"
import type {
  Account,
  CreateAccountRequest,
  CreateCustomerRequest,
  Customer,
  UpdateAccountRequest,
  UpdateCustomerRequest,
} from "../types/api"

export async function listCustomers(): Promise<Customer[]> {
  const data = await apiRequest<{ customers: Customer[] }>("/customers")
  return Array.isArray(data.customers) ? data.customers : []
}

export function getCustomer(customerId: string): Promise<Customer> {
  return apiRequest<Customer>(`/customers/${customerId}`)
}

export function createCustomer(payload: CreateCustomerRequest): Promise<Customer> {
  return apiRequest<Customer>("/customers", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  })
}

export function updateCustomer(
  customerId: string,
  payload: UpdateCustomerRequest,
): Promise<Customer> {
  return apiRequest<Customer>(`/customers/${customerId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  })
}

export function deleteCustomer(customerId: string): Promise<void> {
  return apiRequest<void>(`/customers/${customerId}`, {
    method: "DELETE",
  })
}

export function addAccount(customerId: string, payload: CreateAccountRequest): Promise<Account> {
  return apiRequest<Account>(`/customers/${customerId}/accounts`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  })
}

export function updateAccount(accountId: string, payload: UpdateAccountRequest): Promise<Account> {
  const requestInit: RequestInit = {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  }

  return apiRequest<Account>(`/accounts/${accountId}`, requestInit).catch((error: unknown) => {
    if (error instanceof ApiError && error.status === 404) {
      return apiRequest<Account>(`/customers/accounts/${accountId}`, requestInit)
    }
    throw error
  })
}

export function deleteAccount(accountId: string): Promise<void> {
  const requestInit: RequestInit = {
    method: "DELETE",
  }

  return apiRequest<void>(`/accounts/${accountId}`, requestInit).catch((error: unknown) => {
    if (error instanceof ApiError && error.status === 404) {
      return apiRequest<void>(`/customers/accounts/${accountId}`, requestInit)
    }
    throw error
  })
}
