
import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from 'react'
import { buscarUsuarioAtual, login as loginService, logout as logoutService } from '../services/authService'
import { EVENTO_SESSAO_EXPIRADA, getAccessToken } from '../services/api'
import type { LoginRequest } from '../types/auth'
import type { Usuario } from '../types/usuario'

interface AuthContextValue {
  usuario: Usuario | null
  carregando: boolean
  autenticado: boolean
  login: (dados: LoginRequest) => Promise<Usuario>
  logout: () => void
  refreshUsuario: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [usuario, setUsuario] = useState<Usuario | null>(null)
  const [carregando, setCarregando] = useState(true)

  const refreshUsuario = useCallback(async () => {
    const token = getAccessToken()
    if (!token) {
      setUsuario(null)
      setCarregando(false)
      return
    }
    try {
      const atual = await buscarUsuarioAtual()
      // Não restaura a sessão se ela foi encerrada durante a requisição.
      if (getAccessToken() === token) setUsuario(atual)
    } catch {
      if (getAccessToken() === token) {
        logoutService()
        setUsuario(null)
      }
    } finally {
      setCarregando(false)
    }
  }, [])

  useEffect(() => {
    void refreshUsuario()
  }, [refreshUsuario])

  useEffect(() => {
    // A API avisa quando um JWT expirou ou foi revogado.
    const encerrarSessao = () => {
      setUsuario(null)
      setCarregando(false)
    }
    window.addEventListener(EVENTO_SESSAO_EXPIRADA, encerrarSessao)
    return () => window.removeEventListener(EVENTO_SESSAO_EXPIRADA, encerrarSessao)
  }, [])

  async function login(dados: LoginRequest): Promise<Usuario> {
    await loginService(dados)
    try {
      const atual = await buscarUsuarioAtual()
      setUsuario(atual)
      return atual
    } catch (erro) {
      logoutService()
      setUsuario(null)
      throw erro
    }
  }

  function logout() {
    logoutService()
    setUsuario(null)
  }

  const value: AuthContextValue = {
    usuario,
    carregando,
    autenticado: Boolean(usuario),
    login,
    logout,
    refreshUsuario
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) throw new Error('useAuth precisa ser usado dentro de AuthProvider.')
  return context
}
