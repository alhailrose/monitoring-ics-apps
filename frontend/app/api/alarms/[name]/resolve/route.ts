import { cookies } from 'next/headers'
import { NextResponse, type NextRequest } from 'next/server'

function apiBase() {
  return process.env.BACKEND_URL ?? 'http://localhost:8000/api/v1'
}

async function authToken() {
  const cookieStore = await cookies()
  return cookieStore.get('access_token')?.value
}

export async function POST(
  req: NextRequest,
  { params }: { params: Promise<{ name: string }> },
) {
  const token = await authToken()
  if (!token) return NextResponse.json({ detail: 'Unauthorized' }, { status: 401 })

  const { name } = await params
  const url = new URL(req.url)
  const notes = url.searchParams.get('notes') ?? ''
  const notesParam = notes ? `?notes=${encodeURIComponent(notes)}` : ''

  try {
    const res = await fetch(
      `${apiBase()}/alarms/${encodeURIComponent(name)}/resolve${notesParam}`,
      {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
      },
    )
    const body = await res.text()
    return new Response(body, {
      status: res.status,
      headers: { 'Content-Type': 'application/json' },
    })
  } catch {
    return NextResponse.json({ detail: 'Gagal resolve alarm' }, { status: 502 })
  }
}
