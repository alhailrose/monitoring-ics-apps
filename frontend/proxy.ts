import { NextRequest, NextResponse } from 'next/server'
import { jwtVerify } from 'jose'

const secret = new TextEncoder().encode(process.env.JWT_SECRET)

const PROTECTED = ['/dashboard', '/customers', '/history', '/findings', '/metrics', '/checks']
const PUBLIC = ['/login', '/']

export async function proxy(req: NextRequest) {
  const path = req.nextUrl.pathname
  const isProtected = PROTECTED.some((p) => path.startsWith(p))
  const isPublic = PUBLIC.includes(path)

  const token = req.cookies.get('access_token')?.value
  let session = null
  if (token) {
    try {
      const { payload } = await jwtVerify(token, secret)
      session = payload
    } catch {
      /* expired or invalid */
    }
  }

  if (isProtected && !session) {
    return NextResponse.redirect(new URL('/login', req.nextUrl))
  }
  if (isPublic && session && !path.startsWith('/dashboard')) {
    return NextResponse.redirect(new URL('/dashboard', req.nextUrl))
  }
  return NextResponse.next()
}

export const config = {
  matcher: ['/((?!api|_next/static|_next/image|.*\\.(?:png|ico|svg|jpg|jpeg)$).*)'],
}
