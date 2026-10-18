import { Navigate, Outlet } from 'react-router-dom'
import { Loading } from './Loading'
import { useAuth } from '../contexts/AuthContext'

export function ProtectedRoute() {
  const { carregando, autenticado } = useAuth()

  if (carregando) {
    return <Loading text="Validando sessão..." />
  }

  return autenticado ? <Outlet /> : <Navigate to="/login" replace />
}

export function AdminRoute() {
  const { carregando, usuario } = useAuth()

  if (carregando) {
    return <Loading text="Validando permissões..." />
  }

  if (!usuario) {
    return <Navigate to="/login" replace />
  }

  if (usuario.perfil !== 'administrador') {
    return <Navigate to="/dashboard" replace />
  }

  return <Outlet />
}