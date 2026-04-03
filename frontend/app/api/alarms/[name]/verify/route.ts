import { cookies } from 'next/headers'
import { NextResponse } from 'next/server'

function apiBase() {
  return process.env.BACKEND_URL ?? 'http://localhost:8000/api/v1'
}

async function authToken() {
  const cookieStore = await cookies()
  return cookieStore.get('access_token')?.value
}

export async function POST(
  _req: Request,
  { params }: { params: Promise<{ name: string }> },
) {
  const token = await authToken()
  if (!token) return NextResponse.json({ detail: 'Unauthorized' }, { status: 401 })

  const { name } = await params
  try {
    const res = await fetch(`${apiBase()}/alarms/${encodeURIComponent(name)}/verify`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}` },
    })
    const body = await res.text()
    return new Response(body, {
      status: res.status,
      headers: { 'Content-Type': 'application/json' },
    })
  } catch {
    return NextResponse.json({ detail: 'Gagal verifikasi alarm' }, { status: 502 })
  }
}
