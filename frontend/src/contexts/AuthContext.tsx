import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode
} from 'react'
import { buscarUsuarioAtual, login as loginService, logout as logoutService } from '../services/authService'
import { getAccessToken } from '../services/api'
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
    if (!getAccessToken()) {
      setUsuario(null)
      setCarregando(false)
      return
    }

    try {
      const atual = await buscarUsuarioAtual()
      setUsuario(atual)
    } catch {
      logoutService()
      setUsuario(null)
    } finally {
      setCarregando(false)
    }
  }, [])

  useEffect(() => {
    void refreshUsuario()
  }, [refreshUsuario])

  async function login(dados: LoginRequest) {
    await loginService(dados)
    const atual = await buscarUsuarioAtual()
    setUsuario(atual)
    return atual
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

  if (!context) {
    throw new Error('useAuth precisa ser usado dentro de AuthProvider.')
  }

  return context
}