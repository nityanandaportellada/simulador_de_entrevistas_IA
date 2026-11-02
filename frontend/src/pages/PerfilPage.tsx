
import { useEffect, useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { apiPut } from '../services/api'
import type { Usuario } from '../types/usuario'

function mensagemErro(erro: unknown): string {
  return erro instanceof Error ? erro.message : 'Não foi possível concluir a operação.'
}

export function PerfilPage() {
  const navigate = useNavigate()
  const { usuario, refreshUsuario, logout } = useAuth()
  const [nome, setNome] = useState('')
  const [email, setEmail] = useState('')
  const [senhaAtual, setSenhaAtual] = useState('')
  const [novaSenha, setNovaSenha] = useState('')
  const [confirmacao, setConfirmacao] = useState('')
  const [salvandoDados, setSalvandoDados] = useState(false)
  const [salvandoSenha, setSalvandoSenha] = useState(false)
  const [erroDados, setErroDados] = useState('')
  const [erroSenha, setErroSenha] = useState('')
  const [avisoDados, setAvisoDados] = useState('')

  useEffect(() => {
    setNome(usuario?.nome ?? '')
    setEmail(usuario?.email ?? '')
  }, [usuario?.nome, usuario?.email])

  async function salvarDados(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault()
    if (salvandoDados || salvandoSenha) return
    setErroDados('')
    setAvisoDados('')
    if (nome.trim().length < 2 || nome.trim().length > 150) {
      setErroDados('O nome deve conter de 2 a 150 caracteres.')
      return
    }
    setSalvandoDados(true)
    try {
      await apiPut<Usuario, { nome: string; email: string }>('/usuarios/me', { nome: nome.trim(), email: email.trim() })
      await refreshUsuario()
      setAvisoDados('Nome e e-mail atualizados com sucesso.')
    } catch (falha: unknown) {
      setErroDados(mensagemErro(falha))
    } finally {
      setSalvandoDados(false)
    }
  }

  async function salvarSenha(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault()
    if (salvandoDados || salvandoSenha) return
    setErroSenha('')
    if (!senhaAtual) { setErroSenha('Informe sua senha atual.'); return }
    if (novaSenha.length < 8 || novaSenha.length > 128 || !/[A-Za-zÀ-ÿ]/.test(novaSenha) || !/\d/.test(novaSenha)) {
      setErroSenha('A nova senha deve ter de 8 a 128 caracteres, com pelo menos uma letra e um número.')
      return
    }
    if (novaSenha === senhaAtual) { setErroSenha('A nova senha precisa ser diferente da atual.'); return }
    if (novaSenha !== confirmacao) { setErroSenha('A confirmação não corresponde à nova senha.'); return }
    setSalvandoSenha(true)
    try {
      await apiPut<void, { senha_atual: string; nova_senha: string }>('/usuarios/me/senha', {
        senha_atual: senhaAtual, nova_senha: novaSenha
      })
      // A troca revoga o token anterior. Não mantenha uma sessão inválida aberta.
      setSenhaAtual('')
      setNovaSenha('')
      setConfirmacao('')
      logout()
      navigate('/login', { replace: true })
    } catch (falha: unknown) {
      setErroSenha(mensagemErro(falha))
    } finally {
      setSalvandoSenha(false)
    }
  }

  return (
    <div>
      <div className="page-heading">
        <div><h1>Perfil</h1><p>Consulte e atualize suas informações de acesso ao Simulador de Entrevistas FESP-PR.</p></div>
      </div>
      <section className="panel profile-card" style={{ marginBottom: 20 }}>
        <div className="avatar avatar--large" aria-hidden="true">{usuario?.nome?.trim().charAt(0).toUpperCase() || 'U'}</div>
        <div>
          <h2>{usuario?.nome}</h2>
          <p>{usuario?.email}</p>
          <span className="status status--avaliada">{usuario?.perfil === 'estudante' ? 'Estudante' : 'Administrador'}</span>
        </div>
      </section>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 360px), 1fr))', gap: 16, alignItems: 'start' }}>
        <section className="panel">
          <div className="panel__heading"><h2>Editar meus dados</h2><p>Altere seu nome e endereço de e-mail.</p></div>
          <form onSubmit={(evento) => void salvarDados(evento)} style={{ display: 'grid', gap: 16 }}>
            <label className="field">Nome completo
              <input required minLength={2} maxLength={150} autoComplete="name" value={nome} disabled={salvandoDados || salvandoSenha} onChange={(evento) => setNome(evento.target.value)} />
            </label>
            <label className="field">E-mail
              <input required type="email" maxLength={254} autoComplete="email" value={email} disabled={salvandoDados || salvandoSenha} onChange={(evento) => setEmail(evento.target.value)} />
            </label>
            {erroDados && <p className="alert alert--error" role="alert">{erroDados}</p>}
            {avisoDados && <p className="note" role="status">{avisoDados}</p>}
            <div className="button-row">
              <button type="submit" className="button button--primary" disabled={salvandoDados || salvandoSenha || !usuario}>
                {salvandoDados ? 'Salvando...' : 'Salvar meus dados'}
              </button>
              <button type="button" className="button button--outline" disabled={salvandoDados || salvandoSenha} onClick={() => { setNome(usuario?.nome ?? ''); setEmail(usuario?.email ?? ''); setErroDados(''); setAvisoDados('') }}>
                Desfazer
              </button>
            </div>
          </form>
        </section>
        <section className="panel">
          <div className="panel__heading"><h2>Alterar minha senha</h2><p>Informe a senha atual e escolha uma nova senha.</p></div>
          <form onSubmit={(evento) => void salvarSenha(evento)} style={{ display: 'grid', gap: 16 }}>
            <label className="field">Senha atual
              <input type="password" required autoComplete="current-password" value={senhaAtual} disabled={salvandoSenha || salvandoDados} onChange={(evento) => setSenhaAtual(evento.target.value)} />
            </label>
            <label className="field">Nova senha
              <input type="password" required minLength={8} maxLength={128} autoComplete="new-password" value={novaSenha} disabled={salvandoSenha || salvandoDados} onChange={(evento) => setNovaSenha(evento.target.value)} />
            </label>
            <label className="field">Confirmar nova senha
              <input type="password" required minLength={8} maxLength={128} autoComplete="new-password" value={confirmacao} disabled={salvandoSenha || salvandoDados} onChange={(evento) => setConfirmacao(evento.target.value)} />
            </label>
            <p className="note">A nova senha deve conter pelo menos oito caracteres, uma letra e um número. Após a alteração, será necessário entrar novamente.</p>
            {erroSenha && <p className="alert alert--error" role="alert">{erroSenha}</p>}
            <button type="submit" className="button button--primary" disabled={salvandoSenha || salvandoDados || !usuario}>
              {salvandoSenha ? 'Alterando senha...' : 'Alterar senha'}
            </button>
          </form>
        </section>
      </div>
    </div>
  )
}
