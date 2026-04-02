import { cookies } from 'next/headers'
import { NextResponse, type NextRequest } from 'next/server'

function apiBase() {
  return process.env.BACKEND_URL ?? 'http://localhost:8000/api/v1'
}

async function authToken() {
  const cookieStore = await cookies()
  return cookieStore.get('access_token')?.value
}

export async function GET() {
  const token = await authToken()
  if (!token) return NextResponse.json({ detail: 'Unauthorized' }, { status: 401 })

  try {
    const res = await fetch(`${apiBase()}/settings/aws-template`, {
      headers: { Authorization: `Bearer ${token}` },
      cache: 'no-store',
    })
    const body = await res.text()
    return new Response(body, {
      status: res.status,
      headers: { 'Content-Type': res.headers.get('content-type') || 'application/json' },
    })
  } catch {
    return NextResponse.json({ detail: 'Gagal mengambil template' }, { status: 500 })
  }
}

export async function PUT(req: NextRequest) {
  const token = await authToken()
  if (!token) return NextResponse.json({ detail: 'Unauthorized' }, { status: 401 })

  try {
    const payload = await req.text()
    const res = await fetch(`${apiBase()}/settings/aws-template`, {
      method: 'PUT',
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: payload,
    })
    const body = await res.text()
    return new Response(body, {
      status: res.status,
      headers: { 'Content-Type': res.headers.get('content-type') || 'application/json' },
    })
  } catch {
    return NextResponse.json({ detail: 'Gagal menyimpan template' }, { status: 500 })
  }
}
