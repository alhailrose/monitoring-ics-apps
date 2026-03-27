export class ApiError extends Error {
  status: number
  body: unknown
  isUnauthorized: boolean

  constructor(status: number, body: unknown) {
    const detail = body && typeof body === 'object' && 'detail' in body
      ? String((body as { detail: unknown }).detail)
      : `API error ${status}`
    super(detail)
    this.status = status
    this.body = body
    this.isUnauthorized = status === 401
  }
}

interface FetchOptions extends RequestInit {
  token?: string
}

export async function apiFetch<T>(path: string, options: FetchOptions = {}): Promise<T> {
  const { token, ...rest } = options
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...((rest.headers as Record<string, string>) ?? {}),
  }

  const base = process.env.BACKEND_URL ?? process.env.NEXT_PUBLIC_API_URL
  const res = await fetch(`${base}${path}`, {
    ...rest,
    headers,
  })

  if (!res.ok) {
    const body = await res.json().catch(() => null)
    throw new ApiError(res.status, body)
  }

  if (res.status === 204) return undefined as T

  return res.json() as Promise<T>
}

export async function apiFetchText(path: string, options: FetchOptions = {}): Promise<string> {
  const { token, ...rest } = options
  const headers: Record<string, string> = {
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...((rest.headers as Record<string, string>) ?? {}),
  }

  const base = process.env.BACKEND_URL ?? process.env.NEXT_PUBLIC_API_URL
  const res = await fetch(`${base}${path}`, {
    ...rest,
    headers,
  })

  if (!res.ok) {
    const body = await res.text().catch(() => '')
    throw new ApiError(res.status, body)
  }

  return res.text()
}
