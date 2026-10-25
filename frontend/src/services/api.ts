
const API_URL = import.meta.env.VITE_API_URL?.trim().replace(/\/$/, '') || 'http://127.0.0.1:8000'

export const EVENTO_SESSAO_EXPIRADA = 'simulador:sessao-expirada'

export interface ApiErrorBody {
  detail?: unknown
}

function mensagemErro(detail: unknown, status: number): string {
  if (typeof detail === 'string' && detail.trim()) return detail
  // FastAPI devolve uma lista de objetos com msg quando a validação falha (422).
  if (Array.isArray(detail)) {
    const mensagens = detail.map((item) => {
      if (item && typeof item === 'object' && 'msg' in item && typeof item.msg === 'string') {
        return item.msg
      }
      return null
    }).filter((item): item is string => item !== null)
    if (mensagens.length) return mensagens.join('; ')
  }
  if (status === 0) return 'Não foi possível conectar ao servidor. Verifique sua conexão e tente novamente.'
  if (status === 429) return 'Limite de solicitações atingido. Tente novamente mais tarde.'
  if (status >= 500) return 'O servidor está indisponível no momento. Tente novamente mais tarde.'
  return `Não foi possível concluir a operação (HTTP ${status}).`
}

export class ApiError extends Error {
  status: number
  detail: unknown
  retryAfterSeconds: number | null

  constructor(status: number, detail: unknown, retryAfterSeconds: number | null = null) {
    super(mensagemErro(detail, status))
    this.name = 'ApiError'
    this.status = status
    this.detail = detail
    this.retryAfterSeconds = retryAfterSeconds
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

export async function apiRequest<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getAccessToken()
  const headers = new Headers(options.headers)
  if (options.body && !headers.has('Content-Type')) headers.set('Content-Type', 'application/json')
  if (token) headers.set('Authorization', `Bearer ${token}`)

  let response: Response
  try {
    response = await fetch(`${API_URL}${path}`, { ...options, headers })
  } catch (erro) {
    if (erro instanceof Error && erro.name === 'AbortError') throw erro
    throw new ApiError(0, 'Não foi possível conectar ao servidor. Verifique sua conexão e tente novamente.')
  }

  let data: unknown = null
  if (response.headers.get('content-type')?.includes('application/json')) {
    try {
      data = await response.json()
    } catch {
      if (response.ok) throw new ApiError(response.status, 'O servidor retornou dados inválidos.')
    }
  }

  if (!response.ok) {
    let detail: unknown = null
    if (data && typeof data === 'object' && 'detail' in data) detail = (data as ApiErrorBody).detail
    const retryAfter = response.headers.get('Retry-After')
    const espera = retryAfter && /^\d+$/.test(retryAfter) ? Number(retryAfter) : null
    // Um login inválido não deve encerrar outra sessão por engano.
    if (response.status === 401 && path !== '/auth/login' && token && getAccessToken() === token) {
      clearAccessToken()
      window.dispatchEvent(new Event(EVENTO_SESSAO_EXPIRADA))
    }
    throw new ApiError(response.status, detail, espera)
  }
  return data as T
}

export function apiGet<T>(path: string): Promise<T> {
  return apiRequest<T>(path, { method: 'GET' })
}

export function apiPost<TResponse, TBody = unknown>(path: string, body?: TBody): Promise<TResponse> {
  return apiRequest<TResponse>(path, {
    method: 'POST',
    body: body === undefined ? undefined : JSON.stringify(body)
  })
}

export function apiPut<TResponse, TBody = unknown>(path: string, body?: TBody): Promise<TResponse> {
  return apiRequest<TResponse>(path, {
    method: 'PUT',
    body: body === undefined ? undefined : JSON.stringify(body)
  })
}

export function getApiUrl(): string {
  return API_URL
}
