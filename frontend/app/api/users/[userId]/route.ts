import { cookies } from 'next/headers'
import { NextResponse } from 'next/server'

function apiBase() {
  return process.env.API_URL ?? 'http://localhost:8000/api/v1'
}

async function authToken() {
  const cookieStore = await cookies()
  return cookieStore.get('access_token')?.value
}

export async function DELETE(
  _req: Request,
  { params }: { params: Promise<{ userId: string }> },
) {
  const { userId } = await params
  const token = await authToken()
  if (!token) return NextResponse.json({ detail: 'Unauthorized' }, { status: 401 })

  try {
    const res = await fetch(`${apiBase()}/users/${userId}`, {
      method: 'DELETE',
      headers: { Authorization: `Bearer ${token}` },
    })
    if (res.status === 204) {
      return new Response(null, { status: 204 })
    }
    const body = await res.text()
    return new Response(body, {
      status: res.status,
      headers: {
        'Content-Type': res.headers.get('content-type') || 'application/json',
      },
    })
  } catch {
    return NextResponse.json({ detail: 'Failed to deactivate user' }, { status: 500 })
  }
}
