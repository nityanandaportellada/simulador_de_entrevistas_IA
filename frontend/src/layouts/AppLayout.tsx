import {
  BarChart3,
  ClipboardList,
  FileText,
  History,
  Home,
  LogOut,
  MessageSquareText,
  PlusCircle,
  Target,
  User,
  Users
} from 'lucide-react'
import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { Brand } from '../components/Brand'
import { useAuth } from '../contexts/AuthContext'

export function AppLayout() {
  const { usuario, logout } = useAuth()
  const navigate = useNavigate()

  function sair() {
    logout()
    navigate('/login')
  }

  const estudante = usuario?.perfil === 'estudante'

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <Brand compact />
        <nav className="sidebar__nav">
          <NavLink to={estudante ? '/dashboard' : '/admin'} end>
            <Home size={20} /> Dashboard
          </NavLink>

          {estudante ? (
            <>
              <NavLink to="/entrevistas/nova">
                <PlusCircle size={20} /> Nova entrevista
              </NavLink>
              <NavLink to="/historico">
                <History size={20} /> Histórico
              </NavLink>
              <NavLink to="/relatorios">
                <FileText size={20} /> Relatórios
              </NavLink>
              <NavLink to="/perfil">
                <User size={20} /> Perfil
              </NavLink>
            </>
          ) : (
            <>
              <NavLink to="/admin/usuarios">
                <Users size={20} /> Usuários
              </NavLink>
              <NavLink to="/admin/tipos">
                <ClipboardList size={20} /> Tipos de entrevista
              </NavLink>
              <NavLink to="/admin/competencias">
                <Target size={20} /> Competências
              </NavLink>
              <NavLink to="/admin/criterios">
                <BarChart3 size={20} /> Critérios
              </NavLink>
              <NavLink to="/admin/perguntas">
                <MessageSquareText size={20} /> Perguntas
              </NavLink>
            </>
          )}
        </nav>

        <div className="sidebar__footer">
          <button className="button button--ghost button--full" onClick={sair}>
            <LogOut size={18} />
            Sair
          </button>
          <div className="sidebar__signature">Educação que conecta futuros</div>
        </div>
      </aside>

      <div className="app-main">
        <header className="topbar">
          <div />
          <div className="topbar__user">
            <div className="avatar">
              {usuario?.nome?.trim().charAt(0).toUpperCase() || 'U'}
            </div>
            <div>
              <strong>{usuario?.nome}</strong>
              <span>{usuario?.perfil === 'administrador' ? 'Administrador' : 'Estudante FESP-PR'}</span>
            </div>
          </div>
        </header>

        <main className="page-container">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
