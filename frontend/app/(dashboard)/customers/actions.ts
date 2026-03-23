'use server'

import { revalidatePath } from 'next/cache'
import { getToken } from '@/lib/server-token'
import {
  createCustomer as apiCreateCustomer,
  updateCustomer as apiUpdateCustomer,
  deleteCustomer as apiDeleteCustomer,
  createAccount as apiCreateAccount,
  updateAccount as apiUpdateAccount,
  deleteAccount as apiDeleteAccount,
} from '@/lib/api/customers'

function revalidate() {
  revalidatePath('/customers')
}

export async function createCustomer(formData: FormData): Promise<{ error?: string }> {
  try {
    const token = await getToken()
    const checks = formData.getAll('checks') as string[]
    const slackEnabled = formData.get('slack_enabled') === 'on'
    await apiCreateCustomer(
      {
        name: formData.get('name') as string,
        display_name: formData.get('display_name') as string,
        checks,
        slack_enabled: slackEnabled,
        slack_channel: slackEnabled ? (formData.get('slack_channel') as string) || null : null,
        report_mode: ((formData.get('report_mode') as string) || 'summary') as 'summary' | 'detailed',
        label: (formData.get('label') as string) || null,
      },
      token,
    )
    revalidate()
    return {}
  } catch (e) {
    return { error: e instanceof Error ? e.message : 'Failed to create customer' }
  }
}

export async function updateCustomer(id: string, formData: FormData): Promise<{ error?: string }> {
  try {
    const token = await getToken()
    const checks = formData.getAll('checks') as string[]
    const slackEnabled = formData.get('slack_enabled') === 'on'
    const reportMode = formData.get('report_mode') as string | null
    const label = formData.get('label') as string | null
    await apiUpdateCustomer(
      id,
      {
        display_name: formData.get('display_name') as string,
        checks,
        slack_enabled: slackEnabled,
        slack_channel: slackEnabled ? (formData.get('slack_channel') as string) || null : null,
        ...(reportMode ? { report_mode: reportMode as 'summary' | 'detailed' } : {}),
        ...(label !== null ? { label: label || null } : {}),
      },
      token,
    )
    revalidate()
    return {}
  } catch (e) {
    return { error: e instanceof Error ? e.message : 'Failed to update customer' }
  }
}

export async function deleteCustomer(id: string): Promise<{ error?: string }> {
  try {
    const token = await getToken()
    await apiDeleteCustomer(id, token)
    revalidate()
    return {}
  } catch (e) {
    return { error: e instanceof Error ? e.message : 'Failed to delete customer' }
  }
}

export async function addAccount(customerId: string, formData: FormData): Promise<{ error?: string }> {
  try {
    const token = await getToken()
    const alarmNamesRaw = formData.get('alarm_names') as string | null
    const alarm_names = alarmNamesRaw
      ? alarmNamesRaw.split('\n').map((s) => s.trim()).filter(Boolean)
      : undefined
    await apiCreateAccount(
      customerId,
      {
        profile_name: formData.get('profile_name') as string,
        display_name: formData.get('display_name') as string,
        is_active: formData.get('is_active') === 'on',
        alarm_names,
      },
      token,
    )
    revalidate()
    return {}
  } catch (e) {
    return { error: e instanceof Error ? e.message : 'Failed to add account' }
  }
}

export async function updateAccount(customerId: string, accountId: string, formData: FormData): Promise<{ error?: string }> {
  try {
    const token = await getToken()
    const alarmNamesRaw = formData.get('alarm_names') as string | null
    const alarm_names = alarmNamesRaw !== null
      ? alarmNamesRaw.split('\n').map((s) => s.trim()).filter(Boolean)
      : undefined
    await apiUpdateAccount(
      customerId,
      accountId,
      {
        display_name: formData.get('display_name') as string,
        is_active: formData.get('is_active') === 'on',
        alarm_names,
      },
      token,
    )
    revalidate()
    return {}
  } catch (e) {
    return { error: e instanceof Error ? e.message : 'Failed to update account' }
  }
}

export async function deleteAccount(customerId: string, accountId: string): Promise<{ error?: string }> {
  try {
    const token = await getToken()
    await apiDeleteAccount(customerId, accountId, token)
    revalidate()
    return {}
  } catch (e) {
    return { error: e instanceof Error ? e.message : 'Failed to delete account' }
  }
}
