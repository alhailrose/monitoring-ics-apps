import 'server-only'
import { cookies } from 'next/headers'
import { jwtVerify } from 'jose'
import type { SessionPayload } from '@/lib/types/api'

const secret = new TextEncoder().encode(process.env.JWT_SECRET)

export async function getSession(): Promise<SessionPayload | null> {
  const cookieStore = await cookies()
  const token = cookieStore.get('access_token')?.value
  if (!token) return null
  try {
    const { payload } = await jwtVerify(token, secret)
    return payload as unknown as SessionPayload
  } catch {
    return null
  }
}
