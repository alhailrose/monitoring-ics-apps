import { cookies } from 'next/headers'
import { NextResponse } from 'next/server'

export async function GET() {
  const cookieStore = await cookies()
  const token = cookieStore.get('access_token')?.value
  if (!token) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
  }

  const apiUrl = process.env.BACKEND_URL ?? 'http://localhost:8000/api/v1'
  const res = await fetch(`${apiUrl}/sessions/health`, {
    headers: { Authorization: `Bearer ${token}` },
    cache: 'no-store',
  })

  if (!res.ok) {
    return NextResponse.json({ error: 'Upstream error' }, { status: res.status })
  }

  const data = await res.json()
  return NextResponse.json(data)
}
