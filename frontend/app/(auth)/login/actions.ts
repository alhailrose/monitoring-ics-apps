'use server'
import { redirect } from 'next/navigation'
import { login } from '@/lib/api/auth'
import { setSessionCookie } from '@/lib/session'
import { ApiError } from '@/lib/api/client'

export async function loginAction(_: unknown, formData: FormData) {
  const username = formData.get('username') as string
  const password = formData.get('password') as string
  try {
    const { access_token, expires_at } = await login(username, password)
    await setSessionCookie(access_token, expires_at)
  } catch (e) {
    if (e instanceof ApiError) {
      return { error: 'Invalid username or password' }
    }
    return { error: 'Something went wrong. Please try again.' }
  }
  redirect('/dashboard')
}
