import { cookies } from 'next/headers'
import { NextResponse, type NextRequest } from 'next/server'

function apiBase() {
  return process.env.BACKEND_URL ?? 'http://localhost:8000/api/v1'
}

async function authToken() {
  const cookieStore = await cookies()
  return cookieStore.get('access_token')?.value
}

export async function GET(req: NextRequest) {
  const token = await authToken()
  if (!token) return NextResponse.json({ detail: 'Unauthorized' }, { status: 401 })

  const { searchParams } = new URL(req.url)
  const qs = searchParams.toString()

  try {
    const res = await fetch(`${apiBase()}/mailing${qs ? `?${qs}` : ''}`, {
      headers: { Authorization: `Bearer ${token}` },
      cache: 'no-store',
    })
    const body = await res.text()
    return new Response(body, {
      status: res.status,
      headers: { 'Content-Type': 'application/json' },
    })
  } catch {
    return NextResponse.json({ detail: 'Failed to fetch contacts' }, { status: 500 })
  }
}

export async function POST(req: NextRequest) {
  const token = await authToken()
  if (!token) return NextResponse.json({ detail: 'Unauthorized' }, { status: 401 })

  try {
    const payload = await req.text()
    const res = await fetch(`${apiBase()}/mailing`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: payload,
    })
    const body = await res.text()
    return new Response(body, {
      status: res.status,
      headers: { 'Content-Type': 'application/json' },
    })
  } catch {
    return NextResponse.json({ detail: 'Failed to create contact' }, { status: 500 })
  }
}
