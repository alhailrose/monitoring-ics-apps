/**
 * @jest-environment node
 */

const mockGet = jest.fn()

jest.mock('next/headers', () => ({
  cookies: jest.fn(() => Promise.resolve({ get: mockGet })),
}))

import { GET } from '@/app/api/terminal-token/route'

describe('GET /api/terminal-token', () => {
  beforeEach(() => {
    jest.clearAllMocks()
  })

  it('returns token and disables caching', async () => {
    mockGet.mockReturnValue({ value: 'jwt.admin.token' })

    const response = await GET()
    const body = await response.json()

    expect(response.status).toBe(200)
    expect(body).toEqual({ token: 'jwt.admin.token' })
    expect(response.headers.get('cache-control')).toContain('no-store')
  })

  it('returns 401 and disables caching when cookie is missing', async () => {
    mockGet.mockReturnValue(undefined)

    const response = await GET()
    const body = await response.json()

    expect(response.status).toBe(401)
    expect(body).toEqual({ error: 'Unauthorized' })
    expect(response.headers.get('cache-control')).toContain('no-store')
  })
})
