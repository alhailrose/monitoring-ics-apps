import 'server-only'
import { cookies } from 'next/headers'

export async function getToken(): Promise<string> {
  const cookieStore = await cookies()
  const token = cookieStore.get('access_token')?.value
  if (!token) throw new Error('No access token')
  return token
}
