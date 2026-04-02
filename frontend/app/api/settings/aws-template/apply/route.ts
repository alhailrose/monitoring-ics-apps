import { cookies } from 'next/headers'
import { NextResponse, type NextRequest } from 'next/server'

function apiBase() {
  return process.env.BACKEND_URL ?? 'http://localhost:8000/api/v1'
}

async function authToken() {
  const cookieStore = await cookies()
  return cookieStore.get('access_token')?.value
}

export async function POST(req: NextRequest) {
  const token = await authToken()
  if (!token) return NextResponse.json({ detail: 'Unauthorized' }, { status: 401 })

  try {
    const { username } = await req.json()
    const res = await fetch(`${apiBase()}/settings/aws-template/apply/${encodeURIComponent(username)}`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}` },
    })
    const body = await res.text()
    return new Response(body, {
      status: res.status,
      headers: { 'Content-Type': res.headers.get('content-type') || 'application/json' },
    })
  } catch {
    return NextResponse.json({ detail: 'Gagal menerapkan template' }, { status: 500 })
  }
}
