import { cookies } from 'next/headers'
import { redirect } from 'next/navigation'
import { exchangeCodeForIdToken } from '@/lib/google-oauth'
import { setSessionCookie } from '@/lib/session'
import type { NextRequest } from 'next/server'

const BACKEND_URL = process.env.BACKEND_URL ?? 'http://localhost:8000/api/v1'

export async function GET(req: NextRequest) {
  const { searchParams } = req.nextUrl
  const code = searchParams.get('code')
  const state = searchParams.get('state')

  const cookieStore = await cookies()
  const savedState = cookieStore.get('oauth_state')?.value
  const inviteToken = cookieStore.get('oauth_invite')?.value

  // Clear OAuth cookies
  cookieStore.delete('oauth_state')
  cookieStore.delete('oauth_invite')

  if (!code || !state || state !== savedState) {
    redirect('/login?error=oauth_state')
  }

  let idToken: string
  try {
    idToken = await exchangeCodeForIdToken(code)
  } catch {
    redirect('/login?error=oauth_exchange')
  }

  // If invite token present → accept invite first
  const endpoint = inviteToken
    ? `${BACKEND_URL}/auth/google/accept-invite?invite_token=${inviteToken}`
    : `${BACKEND_URL}/auth/google`

  const res = await fetch(endpoint, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ id_token: idToken }),
  })

  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    if (body?.detail === 'invite_required') {
      redirect('/login?error=invite_required')
    }
    redirect('/login?error=google_auth')
  }

  const { access_token, expires_at } = await res.json()
  await setSessionCookie(access_token, expires_at)
  redirect('/dashboard')
}
