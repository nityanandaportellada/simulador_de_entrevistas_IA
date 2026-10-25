
import { useEffect, useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { apiGet, apiPost, ApiError } from '../services/api'
import { Loading } from './Loading'

type Situacao = 'em_andamento' | 'finalizada' | 'em_analise' | 'avaliada' | 'erro_analise' | 'cancelada'

export interface EntrevistaResumo {
  id: number
  estudante: string
  modalidade: string
  perfil: string
  area: string | null
  subarea: string | null
  status: Situacao
  data_inicio: string
  pontuacao_final: number | null
}

type Resultado = {
  itens: EntrevistaResumo[]
  total: number
  pagina: number
  por_pagina: number
  total_paginas: number
  tipos: { id: number; nome: string }[]
  areas: { id: number; nome: string }[]
}

type Filtros = {
  busca: string; situacao: string; tipo_id: string; perfil: string
  area_id: string; data_de: string; data_ate: string; ordem: string
}

type Detalhe = {
  id: number; estudante: string; modalidade: string; perfil_profissional: string | null
  area: string | null; subarea: string | null; status: Situacao
  data_inicio: string; data_fim: string | null; perguntas: number
  respostas: number; avaliacoes: number; chamadas_registradas: number | null
  limite_chamadas_entrevista: number; pode_solicitar_analise: boolean
  orientacoes: string[]
}

type Props = {
  modo?: 'resumo'; recentes: EntrevistaResumo[]; total: number
  atualizar: number; onDetalhes: (id: number) => void
} | { modo: 'completo' }

const VAZIO: Filtros = {
  busca: '', situacao: '', tipo_id: '', perfil: '', area_id: '',
  data_de: '', data_ate: '', ordem: 'recentes'
}
const SITUACOES: Record<Situacao, string> = {
  em_andamento: 'Em andamento', finalizada: 'Aguardando análise',
  em_analise: 'Em análise', avaliada: 'Avaliada',
  erro_analise: 'Erro na análise', cancelada: 'Cancelada'
}
const PERFIS: Record<string, string> = {
  estagio_trainee: 'Estágio / Trainee', junior: 'Júnior', pleno: 'Pleno',
  senior: 'Sênior', legado: 'Não informado (legado)'
}

function formatarData(valor: string): string {
  const data = new Date(valor.includes('T') ? valor : valor.replace(' ', 'T'))
  return Number.isNaN(data.getTime()) ? valor : data.toLocaleString('pt-BR')
}

function mensagem(erro: unknown): string {
  return erro instanceof Error ? erro.message : 'Não foi possível consultar a entrevista.'
}

export function AdminEntrevistasLista(props: Props) {
  const completo = props.modo === 'completo'
  const [formulario, setFormulario] = useState<Filtros>({ ...VAZIO })
  const [filtros, setFiltros] = useState<Filtros>({ ...VAZIO })
  const [pagina, setPagina] = useState(1)
  const [porPagina, setPorPagina] = useState(15)
  const [resultado, setResultado] = useState<Resultado | null>(null)
  const [carregando, setCarregando] = useState(false)
  const [erro, setErro] = useState('')
  const [erroFiltro, setErroFiltro] = useState('')
  const [atualizar, setAtualizar] = useState(0)
  const [detalheId, setDetalheId] = useState<number | null>(null)
  const [detalhe, setDetalhe] = useState<Detalhe | null>(null)
  const [carregandoDetalhe, setCarregandoDetalhe] = useState(false)
  const [erroDetalhe, setErroDetalhe] = useState('')
  const [avisoDetalhe, setAvisoDetalhe] = useState('')
  const [confirmando, setConfirmando] = useState(false)
  const [reanalisando, setReanalisando] = useState(false)

  // Consulta todas as entrevistas apenas na página administrativa de Entrevistas.
  useEffect(() => {
    if (!completo) return
    let ativo = true
    const parametros = new URLSearchParams({ pagina: String(pagina), por_pagina: String(porPagina), ordem: filtros.ordem })
    for (const campo of ['busca', 'situacao', 'tipo_id', 'perfil', 'area_id', 'data_de', 'data_ate'] as const) {
      const valor = filtros[campo].trim()
      if (valor) parametros.set(campo, valor)
    }
    setCarregando(true)
    setErro('')
    apiGet<Resultado>(`/admin/painel/entrevistas?${parametros.toString()}`)
      .then((dados) => { if (ativo) setResultado(dados) })
      .catch((falha: unknown) => { if (ativo) setErro(mensagem(falha)) })
      .finally(() => { if (ativo) setCarregando(false) })
    return () => { ativo = false }
  }, [completo, filtros, pagina, porPagina, atualizar])

  function alterarCampo(campo: keyof Filtros, valor: string) {
    setFormulario((anterior) => ({ ...anterior, [campo]: valor }))
    setErroFiltro('')
  }

  function aplicar(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault()
    if (formulario.data_de && formulario.data_ate && formulario.data_de > formulario.data_ate) {
      setErroFiltro('A data inicial não pode ser posterior à data final.')
      return
    }
    setPagina(1)
    setFiltros({ ...formulario })
    setAtualizar((valor) => valor + 1)
  }

  function limpar() {
    setFormulario({ ...VAZIO })
    setFiltros({ ...VAZIO })
    setPagina(1)
    setErroFiltro('')
    setAtualizar((valor) => valor + 1)
  }

  async function abrirDetalhes(id: number) {
    if (!completo) return
    setDetalheId(id)
    setDetalhe(null)
    setErroDetalhe('')
    setAvisoDetalhe('')
    setConfirmando(false)
    setCarregandoDetalhe(true)
    try {
      setDetalhe(await apiGet<Detalhe>(`/admin/painel/entrevistas/${id}`))
    } catch (falha: unknown) {
      setErroDetalhe(mensagem(falha))
    } finally {
      setCarregandoDetalhe(false)
    }
  }

  function fecharDetalhes() {
    if (reanalisando) return
    setDetalheId(null)
    setDetalhe(null)
    setErroDetalhe('')
    setConfirmando(false)
  }

  async function repetirAnalise() {
    if (!detalhe || !confirmando || !detalhe.pode_solicitar_analise || reanalisando) return
    const id = detalhe.id
    setReanalisando(true)
    setErroDetalhe('')
    setAvisoDetalhe('')
    try {
      await apiPost<unknown>(`/analise/entrevistas/${id}`)
      setAvisoDetalhe('Análise concluída. O histórico foi atualizado.')
      setAtualizar((valor) => valor + 1)
    } catch (falha: unknown) {
      if (falha instanceof ApiError && falha.status === 429 && falha.retryAfterSeconds !== null) {
        setErroDetalhe(`${falha.message} Aguarde aproximadamente ${Math.ceil(falha.retryAfterSeconds / 60)} minuto(s).`)
      } else setErroDetalhe(mensagem(falha))
    } finally {
      setConfirmando(false)
      try { setDetalhe(await apiGet<Detalhe>(`/admin/painel/entrevistas/${id}`)) }
      catch { /* Mantém a mensagem da solicitação principal. */ }
      setReanalisando(false)
    }
  }

  const registros = completo ? resultado?.itens ?? [] : props.recentes
  const total = completo ? resultado?.total ?? 0 : props.total
  const paginas = resultado?.total_paginas ?? 1

  return (
    <section className="panel" id="historico-entrevistas" style={{ marginTop: 20 }}>
      <div className="panel__heading panel__heading--actions">
        <div>
          <h2>{completo ? 'Histórico completo das entrevistas' : 'Últimas 10 entrevistas'}</h2>
          <p>{completo
            ? 'Pesquise, filtre, ordene e consulte entrevistas de todos os períodos.'
            : `Exibindo as últimas ${registros.length} de ${total} entrevistas cadastradas.`}</p>
        </div>
        {!completo && <Link className="button button--primary" to="/admin/tipos">Ver todas as entrevistas</Link>}
      </div>

      {completo && (
        <form onSubmit={aplicar} style={{ marginBottom: 16 }}>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(min(100%,190px),1fr))', gap: 12 }}>
            <label className="field">Pesquisar por ID, nome, e-mail ou modalidade
              <input maxLength={120} value={formulario.busca} placeholder="ID ou nome do estudante"
                onChange={(evento) => alterarCampo('busca', evento.target.value)} />
            </label>
            <label className="field">Situação
              <select value={formulario.situacao} onChange={(evento) => alterarCampo('situacao', evento.target.value)}>
                <option value="">Todas as situações</option>
                {Object.entries(SITUACOES).map(([chave, nome]) => <option key={chave} value={chave}>{nome}</option>)}
              </select>
            </label>
            <label className="field">Modalidade
              <select value={formulario.tipo_id} onChange={(evento) => alterarCampo('tipo_id', evento.target.value)}>
                <option value="">Todas as modalidades</option>
                {resultado?.tipos.map((tipo) => <option key={tipo.id} value={tipo.id}>{tipo.nome}</option>)}
              </select>
            </label>
            <label className="field">Perfil profissional
              <select value={formulario.perfil} onChange={(evento) => alterarCampo('perfil', evento.target.value)}>
                <option value="">Todos os perfis</option>
                {Object.entries(PERFIS).map(([chave, nome]) => <option key={chave} value={chave}>{nome}</option>)}
              </select>
            </label>
            <label className="field">Área técnica
              <select value={formulario.area_id} onChange={(evento) => alterarCampo('area_id', evento.target.value)}>
                <option value="">Todas as áreas</option>
                {resultado?.areas.map((area) => <option key={area.id} value={area.id}>{area.nome}</option>)}
              </select>
            </label>
            <label className="field">Data inicial
              <input type="date" value={formulario.data_de} onChange={(evento) => alterarCampo('data_de', evento.target.value)} />
            </label>
            <label className="field">Data final
              <input type="date" value={formulario.data_ate} onChange={(evento) => alterarCampo('data_ate', evento.target.value)} />
            </label>
            <label className="field">Ordenar por
              <select value={formulario.ordem} onChange={(evento) => alterarCampo('ordem', evento.target.value)}>
                <option value="recentes">Mais recentes</option>
                <option value="antigas">Mais antigas</option>
                <option value="maior_nota">Maior nota</option>
                <option value="menor_nota">Menor nota</option>
              </select>
            </label>
          </div>
          <div className="button-row" style={{ marginTop: 12, flexWrap: 'wrap', alignItems: 'end' }}>
            <button type="submit" className="button button--primary" disabled={carregando}>Pesquisar / aplicar filtros</button>
            <button type="button" className="button button--outline" disabled={carregando} onClick={limpar}>Limpar filtros</button>
            <label className="field" style={{ minWidth: 105 }}>Por página
              <select value={porPagina} disabled={carregando} onChange={(evento) => { setPorPagina(Number(evento.target.value)); setPagina(1) }}>
                <option value={10}>10</option><option value={15}>15</option><option value={20}>20</option><option value={50}>50</option>
              </select>
            </label>
          </div>
          {erroFiltro && <p role="alert" className="alert alert--error">{erroFiltro}</p>}
          <p className="note">A consulta inclui todo o histórico, independentemente do período dos gráficos do Dashboard.</p>
        </form>
      )}

      {completo && resultado && !erro && (
        <p className="note" role="status">{resultado.total} entrevista(s) encontrada(s). Página {resultado.pagina} de {paginas}.</p>
      )}
      {completo && carregando && <p className="note" role="status">Carregando entrevistas...</p>}
      {completo && erro && (
        <div role="alert"><p className="alert alert--error">{erro}</p>
          <button type="button" className="button button--outline" onClick={() => setAtualizar((valor) => valor + 1)}>Tentar novamente</button>
        </div>
      )}
      {(!completo || (!carregando && !erro)) && (
        <div className="table-wrap">
          <table>
            <thead><tr><th>ID</th><th>Estudante</th><th>Modalidade</th><th>Perfil</th><th>Início</th><th>Situação</th><th>Nota</th><th>Ação</th></tr></thead>
            <tbody>
              {registros.map((item) => (
                <tr key={item.id}>
                  <td>#{item.id}</td><td>{item.estudante}</td><td>{item.modalidade}</td>
                  <td>{PERFIS[item.perfil] ?? item.perfil}</td><td>{formatarData(item.data_inicio)}</td>
                  <td><span className={`status status--${item.status}`}>{SITUACOES[item.status]}</span></td>
                  <td>{item.status === 'avaliada' && item.pontuacao_final !== null && Number.isFinite(item.pontuacao_final)
                    ? item.pontuacao_final.toFixed(2) : '—'}</td>
                  <td><button type="button" className="button button--small button--outline"
                    onClick={() => { if (completo) void abrirDetalhes(item.id); else props.onDetalhes(item.id) }}>Detalhes</button></td>
                </tr>
              ))}
              {registros.length === 0 && <tr><td colSpan={8}>Nenhuma entrevista encontrada.</td></tr>}
            </tbody>
          </table>
        </div>
      )}
      {completo && !carregando && !erro && resultado && paginas > 1 && (
        <div className="button-row" style={{ marginTop: 16, alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap' }}>
          <button type="button" className="button button--outline" disabled={pagina <= 1} onClick={() => setPagina((valor) => Math.max(1, valor - 1))}>Página anterior</button>
          <strong>Página {resultado.pagina} de {paginas}</strong>
          <button type="button" className="button button--outline" disabled={pagina >= paginas} onClick={() => setPagina((valor) => valor + 1)}>Próxima página</button>
        </div>
      )}

      {completo && detalheId !== null && (
        <div role="presentation" style={{ position: 'fixed', inset: 0, zIndex: 1200, background: 'rgba(10,25,60,.65)', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 16 }}>
          <section role="dialog" aria-modal="true" aria-labelledby="titulo-detalhe-historico" className="panel"
            style={{ width: '100%', maxWidth: 680, maxHeight: '90vh', overflowY: 'auto', background: 'white' }}>
            <div className="panel__heading panel__heading--actions">
              <div><h2 id="titulo-detalhe-historico">Entrevista #{detalheId}</h2><p>Diagnóstico administrativo sem exibir respostas.</p></div>
              <button type="button" className="button button--outline" disabled={reanalisando} onClick={fecharDetalhes}>Fechar</button>
            </div>
            {carregandoDetalhe && <Loading />}
            {detalhe && (
              <>
                <div className="interview-summary">
                  <div><span>Estudante</span><strong>{detalhe.estudante}</strong></div>
                  <div><span>Modalidade</span><strong>{detalhe.modalidade}</strong></div>
                  <div><span>Perfil</span><strong>{PERFIS[detalhe.perfil_profissional ?? 'legado']}</strong></div>
                  <div><span>Situação</span><strong>{SITUACOES[detalhe.status]}</strong></div>
                  <div><span>Respostas</span><strong>{detalhe.respostas}</strong></div>
                  <div><span>Avaliações</span><strong>{detalhe.avaliacoes}</strong></div>
                  <div><span>Chamadas registradas</span><strong>{detalhe.chamadas_registradas ?? 'Sem histórico'}</strong></div>
                  <div><span>Limite por entrevista</span><strong>{detalhe.limite_chamadas_entrevista}</strong></div>
                </div>
                <p className="note">Início: {formatarData(detalhe.data_inicio)}. {detalhe.perguntas} perguntas registradas.</p>
                {detalhe.orientacoes.length > 0 && <ul>{detalhe.orientacoes.map((orientacao, indice) => <li key={indice}>{orientacao}</li>)}</ul>}
                {detalhe.pode_solicitar_analise && (
                  <div style={{ marginTop: 16 }}>
                    {!confirmando ? (
                      <button type="button" className="button button--primary" onClick={() => setConfirmando(true)}>Solicitar nova análise</button>
                    ) : (
                      <div style={{ border: '1px solid var(--border)', padding: 12, borderRadius: 10 }}>
                        <p>Uma nova análise pode consumir chamadas pagas da OpenAI e substituir avaliações parciais. Confirma a tentativa?</p>
                        <div className="button-row">
                          <button type="button" className="button button--outline" disabled={reanalisando} onClick={() => setConfirmando(false)}>Cancelar</button>
                          <button type="button" className="button button--primary" disabled={reanalisando} onClick={() => void repetirAnalise()}>
                            {reanalisando ? 'Analisando...' : 'Confirmar nova tentativa'}
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </>
            )}
            {erroDetalhe && <p className="alert alert--error" role="alert">{erroDetalhe}</p>}
            {avisoDetalhe && <p className="note" role="status">{avisoDetalhe}</p>}
          </section>
        </div>
      )}
    </section>
  )
}
