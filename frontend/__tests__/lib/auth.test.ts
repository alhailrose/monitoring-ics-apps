/**
 * @jest-environment node
 */
// Tests for lib/auth.ts getSession()
// Mocks next/headers and jose to avoid server-only boundary issues in Jest

const mockGet = jest.fn()
jest.mock('next/headers', () => ({
  cookies: jest.fn(() => Promise.resolve({ get: mockGet })),
}))

const mockJwtVerify = jest.fn()
jest.mock('jose', () => ({
  jwtVerify: (...args: unknown[]) => mockJwtVerify(...args),
}))

// server-only is a no-op in tests
jest.mock('server-only', () => ({}))

import { getSession } from '@/lib/auth'

describe('getSession', () => {
  beforeEach(() => {
    jest.clearAllMocks()
  })

  it('returns null when no cookie is present', async () => {
    mockGet.mockReturnValue(undefined)
    const result = await getSession()
    expect(result).toBeNull()
  })

  it('returns payload when token is valid', async () => {
    const payload = { sub: '1', username: 'admin', role: 'super_user', exp: 9999999999 }
    mockGet.mockReturnValue({ value: 'valid.token.here' })
    mockJwtVerify.mockResolvedValue({ payload })

    const result = await getSession()
    expect(result).toEqual(payload)
  })

  it('returns null when token is expired or invalid', async () => {
    mockGet.mockReturnValue({ value: 'expired.token' })
    mockJwtVerify.mockRejectedValue(new Error('JWTExpired'))

    const result = await getSession()
    expect(result).toBeNull()
  })
})
