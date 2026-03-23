import 'server-only'
import { cookies } from 'next/headers'

export async function setSessionCookie(token: string, expiresAt: string) {
  const cookieStore = await cookies()
  cookieStore.set('access_token', token, {
    httpOnly: true,
    secure: process.env.NODE_ENV === 'production',
    sameSite: 'lax',
    path: '/',
    expires: new Date(expiresAt),
  })
}

export async function deleteSessionCookie() {
  const cookieStore = await cookies()
  cookieStore.delete('access_token')
}
