import { apiFetch } from './client'
import type { TokenResponse, User } from '@/lib/types/api'

export async function login(username: string, password: string): Promise<TokenResponse> {
  const body = new URLSearchParams({ username, password })
  return apiFetch<TokenResponse>('/auth/login', {
    method: 'POST',
    body,
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  })
}

export async function getMe(token: string): Promise<User> {
  return apiFetch<User>('/auth/me', { token })
}
