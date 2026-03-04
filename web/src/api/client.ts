const API_PREFIX = "/api/v1"
const BACKEND_BASE_HINT = "http://localhost:8080"

const statusMessage = (status: number): string => {
  if (status === 400) return "Request data is invalid. Please review form input."
  if (status === 404) return "Requested resource was not found."
  if (status === 409) return "Conflict detected. Data may already exist."
  if (status === 500) {
    return "Backend server error (500). Please check backend logs and retry."
  }
  if (status === 502 || status === 503 || status === 504) {
    return "Backend service is unavailable. Please try again shortly."
  }
  return `Request failed with status ${status}`
}

export class ApiError extends Error {
  status: number

  constructor(message: string, status: number) {
    super(message)
    this.name = "ApiError"
    this.status = status
  }
}

const isRecord = (value: unknown): value is Record<string, unknown> => {
  return typeof value === "object" && value !== null
}

export const toUserMessage = (error: unknown, fallback: string): string => {
  if (error instanceof ApiError) {
    return error.message || fallback
  }

  if (error instanceof Error) {
    return error.message || fallback
  }

  return fallback
}

export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response
  try {
    response = await fetch(`${API_PREFIX}${path}`, init)
  } catch {
    throw new ApiError(
      `Cannot connect to backend (${BACKEND_BASE_HINT}). Please ensure the API server is running.`,
      0,
    )
  }

  if (response.status === 204) {
    return undefined as T
  }

  const contentType = response.headers?.get?.("content-type") ?? "application/json"
  const isJson = contentType.includes("application/json")

  let payload: unknown = null
  if (isJson) {
    try {
      payload = await response.json()
    } catch {
      payload = null
    }
  } else {
    const text = await response.text()
    payload = text.length > 0 ? text : null
  }

  if (!response.ok) {
    const detail = isRecord(payload) ? payload.detail : null
    const message = typeof detail === "string" && detail.trim().length > 0
      ? detail
      : statusMessage(response.status)
    throw new ApiError(message, response.status)
  }

  return payload as T
}
