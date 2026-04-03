import { cookies } from 'next/headers'
import { redirect } from 'next/navigation'
import { randomBytes } from 'crypto'
import { getGoogleAuthUrl } from '@/lib/google-oauth'
import type { NextRequest } from 'next/server'

export async function GET(req: NextRequest) {
  const inviteToken = req.nextUrl.searchParams.get('invite') ?? undefined
  const state = randomBytes(16).toString('hex')

  const cookieStore = await cookies()
  const secure = process.env.NODE_ENV === 'production'
  cookieStore.set('oauth_state', state, {
    httpOnly: true,
    maxAge: 300,
    sameSite: 'lax',
    path: '/',
    secure,
  })
  if (inviteToken) {
    cookieStore.set('oauth_invite', inviteToken, {
      httpOnly: true,
      maxAge: 300,
      sameSite: 'lax',
      path: '/',
      secure,
    })
  }

  redirect(getGoogleAuthUrl(state, inviteToken))
}
