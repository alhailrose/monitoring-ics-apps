import { apiFetch, ApiError } from '@/lib/api/client'

// Build a minimal mock response without relying on the global Response constructor
const mockResponse = (status: number, body: unknown) => ({
  ok: status >= 200 && status < 300,
  status,
  json: () => Promise.resolve(body),
})

describe('apiFetch', () => {
  beforeEach(() => {
    global.fetch = jest.fn()
  })

  afterEach(() => {
    jest.resetAllMocks()
  })

  it('returns parsed JSON on 200 response', async () => {
    const data = { access_token: 'abc', token_type: 'bearer', expires_at: '2099-01-01' }
    ;(global.fetch as jest.Mock).mockResolvedValueOnce(mockResponse(200, data))

    const result = await apiFetch('/auth/login', { method: 'POST', body: '{}' })
    expect(result).toEqual(data)
  })

  it('throws ApiError with status 404 and isUnauthorized false on 404', async () => {
    ;(global.fetch as jest.Mock).mockResolvedValueOnce(mockResponse(404, { detail: 'Not found' }))

    await expect(apiFetch('/missing')).rejects.toMatchObject({
      status: 404,
      isUnauthorized: false,
    })
  })

  it('throws ApiError with isUnauthorized true on 401', async () => {
    ;(global.fetch as jest.Mock).mockResolvedValueOnce(mockResponse(401, { detail: 'Unauthorized' }))

    await expect(apiFetch('/auth/me')).rejects.toMatchObject({
      status: 401,
      isUnauthorized: true,
    })
  })

  it('attaches Authorization header when token option is provided', async () => {
    ;(global.fetch as jest.Mock).mockResolvedValueOnce(
      mockResponse(200, { id: '1', username: 'admin', role: 'super_user' }),
    )

    await apiFetch('/auth/me', { token: 'my-token' })

    const calledHeaders = (global.fetch as jest.Mock).mock.calls[0][1]
      .headers as Record<string, string>
    expect(calledHeaders['Authorization']).toBe('Bearer my-token')
  })

  it('throws ApiError instance', async () => {
    ;(global.fetch as jest.Mock).mockResolvedValueOnce(mockResponse(500, { detail: 'Server error' }))

    await expect(apiFetch('/fail')).rejects.toBeInstanceOf(ApiError)
  })
})
