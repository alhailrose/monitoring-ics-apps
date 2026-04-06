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
    const res = await fetch(`${apiBase()}/tickets/export${qs ? `?${qs}` : ''}`, {
      headers: { Authorization: `Bearer ${token}` },
      cache: 'no-store',
    })
    if (!res.ok) {
      const body = await res.text()
      return new Response(body, { status: res.status })
    }
    const blob = await res.arrayBuffer()
    return new Response(blob, {
      status: 200,
      headers: {
        'Content-Type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'Content-Disposition': res.headers.get('Content-Disposition') || 'attachment; filename="tickets.xlsx"',
      },
    })
  } catch {
    return NextResponse.json({ detail: 'Failed to export tickets' }, { status: 500 })
  }
}
