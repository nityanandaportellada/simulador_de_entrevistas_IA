import { apiGet, apiPost, clearAccessToken, setAccessToken } from './api'
import type { CadastroRequest, LoginRequest, LoginResponse } from '../types/auth'
import type { Usuario } from '../types/usuario'

export async function login(dados: LoginRequest): Promise<LoginResponse> {
  const resposta = await apiPost<LoginResponse, LoginRequest>('/auth/login', dados)
  setAccessToken(resposta.access_token)
  return resposta
}

export function cadastrar(dados: CadastroRequest): Promise<Usuario> {
  return apiPost<Usuario, CadastroRequest>('/auth/cadastro', dados)
}

export function buscarUsuarioAtual(): Promise<Usuario> {
  return apiGet<Usuario>('/usuarios/me')
}

export function logout(): void {
  clearAccessToken()
}