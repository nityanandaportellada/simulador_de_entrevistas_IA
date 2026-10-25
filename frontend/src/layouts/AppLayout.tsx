
import { useRef, useState, type KeyboardEvent } from 'react'
import {
  BarChart3, ClipboardList, FileText, History, Home, LogOut, Menu,
  MessageSquareText, PlusCircle, Target, User, Users, X
} from 'lucide-react'
import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { Brand } from '../components/Brand'
import { useAuth } from '../contexts/AuthContext'

export function AppLayout() {
  const { usuario, logout } = useAuth()
  const navigate = useNavigate()
  const [menuAberto, setMenuAberto] = useState(false)
  const botaoMenu = useRef<HTMLButtonElement>(null)
  const estudante = usuario?.perfil === 'estudante'

  function fecharMenu() {
    setMenuAberto(false)
  }

  function sair() {
    fecharMenu()
    logout()
    navigate('/login', { replace: true })
  }

  // Permite fechar o menu pelo teclado, devolvendo o foco ao botão.
  function tratarTeclado(evento: KeyboardEvent<HTMLElement>) {
    if (evento.key === 'Escape' && menuAberto) {
      setMenuAberto(false)
      botaoMenu.current?.focus()
    }
  }

  return (
    <>
      <a className="skip-link" href="#conteudo-principal">Pular para o conteúdo principal</a>
      <div className="app-shell">
        <aside className={`sidebar ${menuAberto ? 'sidebar--open' : ''}`} onKeyDown={tratarTeclado}>
          <div className="sidebar__header">
            <Brand compact />
            <button
              ref={botaoMenu}
              type="button"
              className="sidebar__toggle"
              aria-label={menuAberto ? 'Fechar menu de navegação' : 'Abrir menu de navegação'}
              aria-controls="menu-principal"
              aria-expanded={menuAberto}
              onClick={() => setMenuAberto((aberto) => !aberto)}
            >
              {menuAberto ? <X size={22} aria-hidden="true" /> : <Menu size={22} aria-hidden="true" />}
            </button>
          </div>

          <div className="sidebar__collapsible" id="menu-principal">
            <nav className="sidebar__nav" aria-label="Navegação principal">
              <NavLink to={estudante ? '/dashboard' : '/admin'} end onClick={fecharMenu}>
                <Home size={20} aria-hidden="true" /><span>Dashboard</span>
              </NavLink>
              {estudante ? (
                <>
                  <NavLink to="/entrevistas/nova" onClick={fecharMenu}>
                    <PlusCircle size={20} aria-hidden="true" /><span>Nova entrevista</span>
                  </NavLink>
                  <NavLink to="/historico" onClick={fecharMenu}>
                    <History size={20} aria-hidden="true" /><span>Histórico</span>
                  </NavLink>
                  <NavLink to="/relatorios" onClick={fecharMenu}>
                    <FileText size={20} aria-hidden="true" /><span>Relatórios</span>
                  </NavLink>
                  <NavLink to="/perfil" onClick={fecharMenu}>
                    <User size={20} aria-hidden="true" /><span>Perfil</span>
                  </NavLink>
                </>
              ) : (
                <>
                  <NavLink to="/admin/usuarios" onClick={fecharMenu}>
                    <Users size={20} aria-hidden="true" /><span>Usuários</span>
                  </NavLink>
                  <NavLink to="/admin/tipos" onClick={fecharMenu}>
                    <ClipboardList size={20} aria-hidden="true" /><span>Entrevistas</span>
                  </NavLink>
                  <NavLink to="/admin/competencias" onClick={fecharMenu}>
                    <Target size={20} aria-hidden="true" /><span>Competências</span>
                  </NavLink>
                  <NavLink to="/admin/criterios" onClick={fecharMenu}>
                    <BarChart3 size={20} aria-hidden="true" /><span>Critérios</span>
                  </NavLink>
                  <NavLink to="/admin/perguntas" onClick={fecharMenu}>
                    <MessageSquareText size={20} aria-hidden="true" /><span>Perguntas</span>
                  </NavLink>
                </>
              )}
            </nav>
            <div className="sidebar__footer">
              <button type="button" className="button button--ghost button--full" onClick={sair}>
                <LogOut size={18} aria-hidden="true" /><span>Sair</span>
              </button>
              <div className="sidebar__signature">Educação que conecta futuros</div>
            </div>
          </div>
        </aside>

        <div className="app-main">
          <header className="topbar">
            <span className="topbar__title">Simulador de Entrevistas</span>
            <div className="topbar__user">
              <div className="avatar" aria-hidden="true">
                {usuario?.nome?.trim().charAt(0).toUpperCase() || 'U'}
              </div>
              <div>
                <strong>{usuario?.nome}</strong>
                <span>{usuario?.perfil === 'administrador' ? 'Administrador' : 'Estudante FESP-PR'}</span>
              </div>
            </div>
          </header>
          <main className="page-container" id="conteudo-principal" tabIndex={-1}>
            <Outlet />
          </main>
        </div>
      </div>
    </>
  )
}
