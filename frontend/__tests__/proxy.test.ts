/**
 * @jest-environment node
 */
// Tests for middleware.ts route protection logic

const mockJwtVerify = jest.fn()
jest.mock('jose', () => ({
  jwtVerify: (...args: unknown[]) => mockJwtVerify(...args),
}))

import { NextRequest } from 'next/server'
import { proxy } from '@/proxy'

function makeRequest(path: string, token?: string): NextRequest {
  const url = `http://localhost${path}`
  const req = new NextRequest(url)
  if (token) {
    req.cookies.set('access_token', token)
  }
  return req
}

describe('proxy', () => {
  beforeEach(() => {
    jest.clearAllMocks()
  })

  it('redirects unauthenticated user from /dashboard to /login', async () => {
    mockJwtVerify.mockRejectedValue(new Error('invalid'))
    const req = makeRequest('/dashboard')
    const res = await proxy(req)
    expect(res.status).toBe(307)
    expect(res.headers.get('location')).toContain('/login')
  })

  it('redirects authenticated user from /login to /dashboard', async () => {
    mockJwtVerify.mockResolvedValue({ payload: { sub: '1' } })
    const req = makeRequest('/login', 'valid.token')
    const res = await proxy(req)
    expect(res.status).toBe(307)
    expect(res.headers.get('location')).toContain('/dashboard')
  })

  it('allows authenticated user to access /dashboard', async () => {
    mockJwtVerify.mockResolvedValue({ payload: { sub: '1' } })
    const req = makeRequest('/dashboard', 'valid.token')
    const res = await proxy(req)
    // NextResponse.next() has no redirect location
    expect(res.headers.get('location')).toBeNull()
  })

  it('allows unauthenticated user to access /login', async () => {
    const req = makeRequest('/login')
    const res = await proxy(req)
    expect(res.headers.get('location')).toBeNull()
  })
})
