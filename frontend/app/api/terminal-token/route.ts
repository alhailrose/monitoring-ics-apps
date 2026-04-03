import { cookies } from 'next/headers'
import { NextResponse } from 'next/server'

export const dynamic = 'force-dynamic'

const NO_STORE_HEADERS = {
  'Cache-Control': 'no-store, no-cache, must-revalidate, proxy-revalidate',
  Pragma: 'no-cache',
  Expires: '0',
}

export async function GET() {
  const cookieStore = await cookies()
  const token = cookieStore.get('access_token')?.value
  if (!token) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401, headers: NO_STORE_HEADERS })
  }
  return NextResponse.json({ token }, { headers: NO_STORE_HEADERS })
}
