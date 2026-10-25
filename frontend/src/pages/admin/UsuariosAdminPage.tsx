
import { useEffect, useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { Loading } from '../../components/Loading'
import { useAuth } from '../../contexts/AuthContext'
import { adminService } from '../../services/adminService'
import type { PerfilUsuario, Usuario } from '../../types/usuario'

type Acao = 'criar' | 'editar' | 'senha' | null
type Coluna = 'id' | 'nome' | 'email' | 'perfil' | 'ativo' | 'acoes'
const comparar = new Intl.Collator('pt-BR', { sensitivity: 'base', numeric: true })
const COLUNAS: { id: Coluna; nome: string }[] = [
  { id: 'id', nome: 'ID' }, { id: 'nome', nome: 'Nome' }, { id: 'email', nome: 'E-mail' },
  { id: 'perfil', nome: 'Perfil' }, { id: 'ativo', nome: 'Ativo' }, { id: 'acoes', nome: 'Ações' }
]

function mensagem(erro: unknown) {
  return erro instanceof Error ? erro.message : 'Não foi possível concluir a operação.'
}

export function UsuariosAdminPage() {
  const navigate = useNavigate()
  const { usuario: atual, logout, refreshUsuario } = useAuth()
  const [items, setItems] = useState<Usuario[]>([])
  const [loading, setLoading] = useState(true)
  const [ocupado, setOcupado] = useState(false)
  const [acao, setAcao] = useState<Acao>(null)
  const [selecionado, setSelecionado] = useState<Usuario | null>(null)
  const [nome, setNome] = useState('')
  const [email, setEmail] = useState('')
  const [perfil, setPerfil] = useState<PerfilUsuario>('estudante')
  const [senha, setSenha] = useState('')
  const [confirmacao, setConfirmacao] = useState('')
  const [senhaAtual, setSenhaAtual] = useState('')
  const [erro, setErro] = useState('')
  const [aviso, setAviso] = useState('')
  const [busca, setBusca] = useState('')
  const [filtroPerfil, setFiltroPerfil] = useState('todos')
  const [filtroAtivo, setFiltroAtivo] = useState('todos')
  const [ordenacao, setOrdenacao] = useState<{ coluna: Coluna; direcao: 'asc' | 'desc' }>({ coluna: 'id', direcao: 'asc' })

  async function carregar() {
    setLoading(true)
    try {
      setItems(await adminService.usuarios())
    } catch (falha: unknown) {
      setErro(mensagem(falha))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { void carregar() }, [])

  const filtrados = items.filter((item) => {
    const termo = busca.trim().toLocaleLowerCase('pt-BR')
    const corresponde = !termo || String(item.id) === termo || item.nome.toLocaleLowerCase('pt-BR').includes(termo) || item.email.toLocaleLowerCase('pt-BR').includes(termo)
    return corresponde && (filtroPerfil === 'todos' || item.perfil === filtroPerfil) &&
      (filtroAtivo === 'todos' || (filtroAtivo === 'ativos' ? item.ativo : !item.ativo))
  })

  function valorOrdenacao(item: Usuario, coluna: Coluna): string | number {
    if (coluna === 'id') return item.id
    if (coluna === 'nome') return item.nome
    if (coluna === 'email') return item.email
    if (coluna === 'perfil') return item.perfil
    if (coluna === 'ativo') return item.ativo ? 1 : 0
    return item.ativo ? 'Inativar' : 'Ativar'
  }

  filtrados.sort((a, b) => {
    const x = valorOrdenacao(a, ordenacao.coluna)
    const y = valorOrdenacao(b, ordenacao.coluna)
    const ordem = typeof x === 'number' && typeof y === 'number' ? x - y : comparar.compare(String(x), String(y))
    return ordem === 0 ? a.id - b.id : ordem * (ordenacao.direcao === 'asc' ? 1 : -1)
  })

  function ordenar(coluna: Coluna) {
    setOrdenacao((anterior) => ({ coluna, direcao: anterior.coluna === coluna && anterior.direcao === 'asc' ? 'desc' : 'asc' }))
  }

  function abrir(novaAcao: Exclude<Acao, null>, item: Usuario | null = null) {
    setAcao(novaAcao)
    setSelecionado(item)
    setNome(item?.nome ?? '')
    setEmail(item?.email ?? '')
    setPerfil(item?.perfil ?? 'estudante')
    setSenha('')
    setConfirmacao('')
    setSenhaAtual('')
    setErro('')
    setAviso('')
  }

  function fechar() {
    if (ocupado) return
    setAcao(null)
    setSelecionado(null)
    setSenha('')
    setConfirmacao('')
    setSenhaAtual('')
    setErro('')
  }

  async function salvar(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault()
    if (!acao || ocupado) return
    setErro('')
    setAviso('')
    if (acao !== 'senha' && (nome.trim().length < 2 || nome.trim().length > 150)) {
      setErro('Informe um nome de 2 a 150 caracteres.')
      return
    }
    if (acao !== 'editar') {
      if (senha.length < 8 || senha.length > 128 || !/[A-Za-zÀ-ÿ]/.test(senha) || !/\d/.test(senha)) {
        setErro('A senha deve ter de 8 a 128 caracteres, ao menos uma letra e um número.')
        return
      }
      if (senha !== confirmacao) {
        setErro('A senha e a confirmação não conferem.')
        return
      }
    }
    setOcupado(true)
    try {
      if (acao === 'criar') {
        await adminService.criarUsuario({ nome: nome.trim(), email: email.trim(), senha, perfil })
        setAviso('Usuário cadastrado com sucesso.')
      } else if (acao === 'editar' && selecionado) {
        await adminService.editarUsuario(selecionado.id, { nome: nome.trim(), email: email.trim() })
        if (selecionado.id === atual?.id) await refreshUsuario()
        setAviso('Dados do usuário atualizados com sucesso.')
      } else if (acao === 'senha' && selecionado) {
        const proprio = selecionado.id === atual?.id
        await adminService.redefinirSenhaUsuario(selecionado.id, { nova_senha: senha, ...(proprio ? { senha_atual: senhaAtual } : {}) })
        if (proprio) {
          logout()
          navigate('/login', { replace: true })
          return
        }
        setAviso('Senha alterada. As sessões anteriores desse usuário foram invalidadas.')
      }
      setAcao(null)
      setSelecionado(null)
      setSenha('')
      setConfirmacao('')
      setSenhaAtual('')
      await carregar()
    } catch (falha: unknown) {
      setErro(mensagem(falha))
    } finally {
      setOcupado(false)
    }
  }

  async function alternarAtivo(item: Usuario) {
    if (ocupado) return
    if (item.id === atual?.id && item.ativo) {
      setErro('Você não pode inativar sua própria conta.')
      return
    }
    setOcupado(true)
    setErro('')
    setAviso('')
    try {
      if (item.ativo) await adminService.inativarUsuario(item.id)
      else await adminService.ativarUsuario(item.id)
      setAviso(item.ativo ? 'Usuário inativado.' : 'Usuário ativado.')
      await carregar()
    } catch (falha: unknown) {
      setErro(mensagem(falha))
    } finally {
      setOcupado(false)
    }
  }

  async function alternarPerfil(item: Usuario) {
    if (ocupado) return
    if (item.id === atual?.id) {
      setErro('Você não pode alterar seu próprio perfil.')
      return
    }
    setOcupado(true)
    setErro('')
    setAviso('')
    try {
      await adminService.alterarPerfil(item.id, { perfil: item.perfil === 'administrador' ? 'estudante' : 'administrador' })
      setAviso('Perfil alterado com sucesso.')
      await carregar()
    } catch (falha: unknown) {
      setErro(mensagem(falha))
    } finally {
      setOcupado(false)
    }
  }

  const proprio = selecionado?.id === atual?.id
  const titulo = acao === 'criar' ? 'Cadastrar usuário' : acao === 'editar' ? 'Editar usuário' : 'Alterar senha'
  if (loading && items.length === 0 && !erro) return <Loading />

  return (
    <div>
      <div className="page-heading">
        <div>
          <h1>Gestão de usuários</h1>
          <p>Cadastre, filtre, classifique, edite e gerencie o acesso dos usuários.</p>
        </div>
        <button type="button" className="button button--primary" disabled={ocupado || loading} onClick={() => abrir('criar')}>Cadastrar usuário</button>
      </div>
      {erro && !acao && <p className="alert alert--error" role="alert">{erro}</p>}
      {aviso && !acao && <p className="note" role="status">{aviso}</p>}
      <section className="panel">
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(min(100%, 190px), 1fr))', gap: 12, marginBottom: 12 }}>
          <label className="field">
            Buscar por ID, nome ou e-mail
            <input value={busca} placeholder="Pesquisar usuário..." onChange={(evento) => setBusca(evento.target.value)} />
          </label>
          <label className="field">
            Perfil
            <select value={filtroPerfil} onChange={(evento) => setFiltroPerfil(evento.target.value)}>
              <option value="todos">Todos os perfis</option>
              <option value="estudante">Estudante</option>
              <option value="administrador">Administrador</option>
            </select>
          </label>
          <label className="field">
            Situação
            <select value={filtroAtivo} onChange={(evento) => setFiltroAtivo(evento.target.value)}>
              <option value="todos">Todos</option>
              <option value="ativos">Ativos</option>
              <option value="inativos">Inativos</option>
            </select>
          </label>
        </div>
        <div className="button-row" style={{ marginBottom: 10 }}>
          <button type="button" className="button button--small button--outline" onClick={() => { setBusca(''); setFiltroPerfil('todos'); setFiltroAtivo('todos') }}>Limpar filtros</button>
          <span className="note">Exibindo {filtrados.length} de {items.length} usuários. Clique nas colunas para ordenar ↑ ou ↓.</span>
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                {COLUNAS.map((coluna) => {
                  const ativa = ordenacao.coluna === coluna.id
                  return (
                    <th key={coluna.id} scope="col" aria-sort={ativa ? ordenacao.direcao === 'asc' ? 'ascending' : 'descending' : 'none'}>
                      <button type="button" title={`Ordenar por ${coluna.nome}`} onClick={() => ordenar(coluna.id)}
                        style={{ border: 0, background: 'transparent', color: 'inherit', cursor: 'pointer', font: 'inherit', fontWeight: 'inherit', textTransform: 'inherit', padding: 0, whiteSpace: 'nowrap' }}>
                        {coluna.nome} {ativa ? ordenacao.direcao === 'asc' ? '↑' : '↓' : '↕'}
                      </button>
                    </th>
                  )
                })}
              </tr>
            </thead>
            <tbody>
              {filtrados.map((item) => (
                <tr key={item.id}>
                  <td>{item.id}</td>
                  <td>{item.nome}</td>
                  <td>{item.email}</td>
                  <td><span className="pill">{item.perfil === 'administrador' ? 'Administrador' : 'Estudante'}</span></td>
                  <td><span className={`status ${item.ativo ? 'status--avaliada' : 'status--erro_analise'}`}>{item.ativo ? 'Ativo' : 'Inativo'}</span></td>
                  <td>
                    <div className="button-row">
                      <button type="button" className="button button--small button--outline" disabled={ocupado || !item.ativo} onClick={() => abrir('editar', item)}>Editar</button>
                      <button type="button" className="button button--small button--outline" disabled={ocupado || !item.ativo} onClick={() => abrir('senha', item)}>Alterar senha</button>
                      <button type="button" className="button button--small button--outline" disabled={ocupado || item.id === atual?.id} onClick={() => void alternarPerfil(item)}>
                        {item.perfil === 'administrador' ? 'Tornar estudante' : 'Tornar admin'}
                      </button>
                      <button type="button" className="button button--small button--ghost" disabled={ocupado || (item.id === atual?.id && item.ativo)} onClick={() => void alternarAtivo(item)}>
                        {item.ativo ? 'Inativar' : 'Ativar'}
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
              {filtrados.length === 0 && <tr><td colSpan={6}>Nenhum usuário corresponde aos filtros.</td></tr>}
            </tbody>
          </table>
        </div>
      </section>
      {acao && (
        <div role="presentation" style={{ position: 'fixed', inset: 0, zIndex: 1000, background: 'rgba(10,25,60,.55)', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 16 }}>
          <section role="dialog" aria-modal="true" aria-labelledby="titulo-usuario" className="panel"
            style={{ width: '100%', maxWidth: 560, maxHeight: '90vh', overflowY: 'auto', background: 'white' }}>
            <h2 id="titulo-usuario">{titulo}{selecionado ? ` — ${selecionado.nome}` : ''}</h2>
            <form onSubmit={(evento) => void salvar(evento)} style={{ display: 'grid', gap: 16, marginTop: 20 }}>
              {acao !== 'senha' && (
                <>
                  <label className="field">
                    Nome completo
                    <input required minLength={2} maxLength={150} autoComplete="name" value={nome} disabled={ocupado} onChange={(evento) => setNome(evento.target.value)} />
                  </label>
                  <label className="field">
                    E-mail
                    <input type="email" required maxLength={254} autoComplete="email" value={email} disabled={ocupado} onChange={(evento) => setEmail(evento.target.value)} />
                  </label>
                  {acao === 'criar' && (
                    <label className="field">
                      Perfil inicial
                      <select value={perfil} disabled={ocupado} onChange={(evento) => setPerfil(evento.target.value as PerfilUsuario)}>
                        <option value="estudante">Estudante</option>
                        <option value="administrador">Administrador</option>
                      </select>
                    </label>
                  )}
                  {acao === 'editar' && <p className="note">Para alterar perfil ou ativar/inativar, utilize os botões da tabela.</p>}
                </>
              )}
              {acao !== 'editar' && (
                <>
                  {acao === 'senha' && proprio && (
                    <label className="field">
                      Sua senha atual
                      <input type="password" required autoComplete="current-password" value={senhaAtual} disabled={ocupado} onChange={(evento) => setSenhaAtual(evento.target.value)} />
                    </label>
                  )}
                  <label className="field">
                    {acao === 'criar' ? 'Senha inicial' : 'Nova senha'}
                    <input type="password" required minLength={8} maxLength={128} autoComplete="new-password" value={senha} disabled={ocupado} onChange={(evento) => setSenha(evento.target.value)} />
                  </label>
                  <label className="field">
                    Confirmar senha
                    <input type="password" required minLength={8} maxLength={128} autoComplete="new-password" value={confirmacao} disabled={ocupado} onChange={(evento) => setConfirmacao(evento.target.value)} />
                  </label>
                  <p className="note">Mínimo de oito caracteres, com letra e número. A alteração invalida as sessões anteriores.</p>
                  {acao === 'senha' && proprio && <p className="note">Você precisará entrar novamente após alterar sua senha.</p>}
                </>
              )}
              {erro && <p className="alert alert--error" role="alert">{erro}</p>}
              <div className="button-row button-row--end">
                <button type="button" className="button button--ghost" disabled={ocupado} onClick={fechar}>Cancelar</button>
                <button type="submit" className="button button--primary" disabled={ocupado}>
                  {ocupado ? 'Salvando...' : acao === 'criar' ? 'Cadastrar' : 'Salvar alterações'}
                </button>
              </div>
            </form>
          </section>
        </div>
      )}
    </div>
  )
}
