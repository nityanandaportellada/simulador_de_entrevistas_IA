const API_URL =
  import.meta.env.VITE_API_URL?.trim() || 'http://127.0.0.1:8000'

export interface ApiErrorBody {
  detail: string | unknown
}

export class ApiError extends Error {
  status: number
  detail: unknown

  constructor(status: number, detail: unknown) {
    super(typeof detail === 'string' ? detail : 'Erro ao comunicar com a API.')
    this.name = 'ApiError'
    this.status = status
    this.detail = detail
  }
}

export function getAccessToken(): string | null {
  return localStorage.getItem('access_token')
}

export function setAccessToken(token: string): void {
  localStorage.setItem('access_token', token)
}

export function clearAccessToken(): void {
  localStorage.removeItem('access_token')
}

export async function apiRequest<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const token = getAccessToken()
  const headers = new Headers(options.headers)

  if (options.body && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }

  if (token) {
    headers.set('Authorization', `Bearer ${token}`)
  }

  const response = await fetch(`${API_URL}${path}`, {
    ...options,
    headers
  })

  let data: unknown = null
  const contentType = response.headers.get('content-type')

  if (contentType?.includes('application/json')) {
    data = await response.json()
  }

  if (!response.ok) {
    let detail: unknown = `Erro HTTP ${response.status}`

    if (data && typeof data === 'object' && 'detail' in data) {
      detail = (data as ApiErrorBody).detail
    }

    if (response.status === 401) {
      clearAccessToken()
    }

    throw new ApiError(response.status, detail)
  }

  return data as T
}

export function apiGet<T>(path: string): Promise<T> {
  return apiRequest<T>(path, { method: 'GET' })
}

export function apiPost<TResponse, TBody = unknown>(
  path: string,
  body?: TBody
): Promise<TResponse> {
  return apiRequest<TResponse>(path, {
    method: 'POST',
    body: body === undefined ? undefined : JSON.stringify(body)
  })
}

export function apiPut<TResponse, TBody = unknown>(
  path: string,
  body?: TBody
): Promise<TResponse> {
  return apiRequest<TResponse>(path, {
    method: 'PUT',
    body: body === undefined ? undefined : JSON.stringify(body)
  })
}

export function getApiUrl(): string {
  return API_URL
}