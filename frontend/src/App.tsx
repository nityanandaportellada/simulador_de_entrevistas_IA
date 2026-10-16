import { Navigate, Route, Routes } from 'react-router-dom'
import { ProtectedRoute, AdminRoute } from './components/ProtectedRoute'
import { AppLayout } from './layouts/AppLayout'
import { LoginPage } from './pages/LoginPage'
import { CadastroPage } from './pages/CadastroPage'
import { DashboardPage } from './pages/DashboardPage'
import { NovaEntrevistaPage } from './pages/NovaEntrevistaPage'
import { EntrevistaPage } from './pages/EntrevistaPage'
import { HistoricoPage } from './pages/HistoricoPage'
import { RelatoriosPage } from './pages/RelatoriosPage'
import { RelatorioPage } from './pages/RelatorioPage'
import { PerfilPage } from './pages/PerfilPage'
import { AdminDashboardPage } from './pages/AdminDashboardPage'
import { UsuariosAdminPage } from './pages/admin/UsuariosAdminPage'
import { CatalogoAdminPage } from './pages/admin/CatalogoAdminPage'
import { PerguntasAdminPage } from './pages/admin/PerguntasAdminPage'

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/cadastro" element={<CadastroPage />} />

      <Route element={<ProtectedRoute />}>
        <Route element={<AppLayout />}>
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/entrevistas/nova" element={<NovaEntrevistaPage />} />
          <Route path="/entrevistas/:id" element={<EntrevistaPage />} />
          <Route path="/historico" element={<HistoricoPage />} />
          <Route path="/relatorios" element={<RelatoriosPage />} />
          <Route path="/relatorios/:id" element={<RelatorioPage />} />
          <Route path="/perfil" element={<PerfilPage />} />

          <Route element={<AdminRoute />}>
            <Route path="/admin" element={<AdminDashboardPage />} />
            <Route path="/admin/usuarios" element={<UsuariosAdminPage />} />
            <Route path="/admin/tipos" element={<CatalogoAdminPage mode="tipos" />} />
            <Route path="/admin/competencias" element={<CatalogoAdminPage mode="competencias" />} />
            <Route path="/admin/criterios" element={<CatalogoAdminPage mode="criterios" />} />
            <Route path="/admin/perguntas" element={<PerguntasAdminPage />} />
          </Route>
        </Route>
      </Route>

      <Route path="/" element={<Navigate to="/login" replace />} />
      <Route path="*" element={<Navigate to="/login" replace />} />
    </Routes>
  )
}
