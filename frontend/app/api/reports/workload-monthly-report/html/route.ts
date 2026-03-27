import { cookies } from 'next/headers'
import { NextResponse, type NextRequest } from 'next/server'

export async function GET(req: NextRequest) {
  const cookieStore = await cookies()
  const token = cookieStore.get('access_token')?.value
  if (!token) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })

  const query = req.nextUrl.searchParams.toString()
  const apiUrl = process.env.API_URL ?? 'http://localhost:8000/api/v1'
  const target = `${apiUrl}/metrics/workload-monthly-report/html${query ? `?${query}` : ''}`

  try {
    const res = await fetch(target, {
      headers: { Authorization: `Bearer ${token}` },
    })
    const body = await res.text()
    return new Response(body, {
      status: res.status,
      headers: {
        'Content-Type': res.headers.get('content-type') || 'text/html; charset=utf-8',
      },
    })
  } catch {
    return NextResponse.json({ error: 'Failed to generate HTML report' }, { status: 500 })
  }
}
