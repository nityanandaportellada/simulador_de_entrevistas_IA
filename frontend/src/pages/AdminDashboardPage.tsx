
import { useEffect, useState, type FormEvent } from 'react'
import { Activity, AlertTriangle, BarChart3, BookOpen, BrainCircuit, CheckCircle2, ClipboardList, Clock3, MessageSquareText, RefreshCw, Target, Users } from 'lucide-react'
import { Link } from 'react-router-dom'
import { Loading } from '../components/Loading'
import { MetricCard } from '../components/MetricCard'
import { ConfiguracaoIA } from '../components/ConfiguracaoIA'
import { AdminEntrevistasLista, type EntrevistaResumo } from '../components/AdminEntrevistasLista'
import { apiGet, apiPost, ApiError } from '../services/api'

type NomeQuantidade = { nome: string; quantidade: number }
type Perfil = 'estagio_trainee' | 'junior' | 'pleno' | 'senior' | 'legado'
type Situacao = 'em_andamento' | 'finalizada' | 'em_analise' | 'avaliada' | 'erro_analise' | 'cancelada'
type Alerta = { titulo: string; detalhe: string; gravidade: 'alta' | 'media' | 'informativa' }
type CoberturaPendente = { tipo: string; area: string | null; subarea: string | null; perfil: Perfil; motivo: string }
type EntrevistaErro = { id: number; estudante: string; modalidade: string; perfil: Perfil; data_inicio: string }
type Detalhe = {
  id: number; estudante: string; modalidade: string; perfil_profissional: Perfil | null
  area: string | null; subarea: string | null; status: Situacao; data_inicio: string; data_fim: string | null
  perguntas: number; respostas: number; avaliacoes: number; chamadas_registradas: number | null
  limite_chamadas_entrevista: number; pode_solicitar_analise: boolean
  motivo_tecnico_registrado: string | null; orientacoes: string[]
}
interface PainelAdmin {
  periodo_dias: number; periodo_inicio: string; periodo_fim: string
  cadastros: { usuarios: number; usuarios_ativos: number; tipos: number; competencias: number; criterios: number; perguntas: number; perguntas_ativas: number; perguntas_inativas: number; sem_referencia: number; soma_pesos_criterios: number }
  entrevistas: { total: number; iniciadas_periodo: number; avaliadas_periodo: number; em_andamento: number; finalizadas_pendentes: number; em_analise: number; erro_analise: number; avaliadas_total: number; canceladas: number; nota_media_periodo: number | null }
  serie: { dia: string; iniciadas: number; avaliadas: number }[]
  modalidades: NomeQuantidade[]; perfis: NomeQuantidade[]; areas: NomeQuantidade[]
  medias_modalidades: { nome: string; media: number; quantidade: number }[]
  medias_areas: { nome: string; media: number; quantidade: number }[]
  dificuldades: NomeQuantidade[]; perguntas_por_tipo: NomeQuantidade[]
  ia: { chamadas_hoje: number; limite_diario: number; registros_disponiveis: boolean; percentual: number; erros_analise: number }
  cobertura: { total_contextos: number; contextos_prontos: number; total_pendentes: number; pendentes: CoberturaPendente[] }
  alertas: Alerta[]; recentes: EntrevistaResumo[]; entrevistas_com_erro: EntrevistaErro[]
}
const PERFIS: Record<string, string> = { estagio_trainee: 'Estágio / Trainee', junior: 'Júnior', pleno: 'Pleno', senior: 'Sênior', legado: 'Não informado (legado)' }
const SITUACOES: Record<Situacao, string> = { em_andamento: 'Em andamento', finalizada: 'Aguardando análise', em_analise: 'Em análise', avaliada: 'Avaliada', erro_analise: 'Erro na análise', cancelada: 'Cancelada' }
const DIFICULDADES: Record<string, string> = { basica: 'Básica', intermediaria: 'Intermediária', avancada: 'Avançada' }
function mensagem(erro: unknown) { return erro instanceof Error ? erro.message : 'Não foi possível concluir a operação.' }
function dataBrasileira(valor: string) {
  const data = new Date(valor.includes('T') ? valor : valor.replace(' ', 'T'))
  return Number.isNaN(data.getTime()) ? valor : data.toLocaleString('pt-BR')
}

function Distribuicao({ titulo, dados, nomes }: { titulo: string; dados: NomeQuantidade[]; nomes?: Record<string, string> }) {
  const maior = Math.max(1, ...dados.map((item) => item.quantidade))
  return <section className="panel" style={{ minWidth: 0 }}>
    <h2 style={{ fontSize: '1.12rem' }}>{titulo}</h2>
    {dados.length === 0 ? <p className="note">Nenhum registro no período.</p> : <div style={{ display: 'grid', gap: 13, marginTop: 18 }}>
      {dados.slice(0, 10).map((item) => <div key={item.nome} style={{ display: 'grid', gap: 5 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: 10, fontSize: '.86rem' }}>
          <span>{nomes?.[item.nome] ?? item.nome}</span><strong>{item.quantidade}</strong>
        </div>
        <div style={{ height: 9, borderRadius: 20, background: 'var(--soft-blue)', overflow: 'hidden' }}>
          <div style={{ height: '100%', width: `${item.quantidade / maior * 100}%`, background: 'var(--blue)', borderRadius: 20 }} />
        </div>
      </div>)}
      {dados.length > 10 && <p className="note">Exibindo as dez categorias mais frequentes.</p>}
    </div>}
  </section>
}
function Medias({ titulo, dados }: { titulo: string; dados: PainelAdmin['medias_modalidades'] }) {
  return <section className="panel" style={{ minWidth: 0 }}><h2 style={{ fontSize: '1.12rem' }}>{titulo}</h2>
    {dados.length === 0 ? <p className="note">Sem avaliações publicadas no período.</p> : <div style={{ display: 'grid', gap: 12, marginTop: 15 }}>
      {dados.slice(0, 10).map((item) => <div key={item.nome}>
        <div style={{ display: 'flex', justifyContent: 'space-between', gap: 10 }}>
          <span>{item.nome} <small>({item.quantidade})</small></span><strong>{item.media.toFixed(2)}/10</strong>
        </div>
        <div className="progress" style={{ marginTop: 6 }} role="progressbar" aria-label={`Média ${item.nome}`} aria-valuemin={0} aria-valuemax={10} aria-valuenow={item.media}>
          <div style={{ width: `${Math.max(0, Math.min(100, item.media * 10))}%` }} />
        </div>
      </div>)}
    </div>}
  </section>
}
function Grafico({ serie }: { serie: PainelAdmin['serie'] }) {
  const passo = Math.max(1, Math.ceil(serie.length / 12))
  const grupos: { rotulo: string; iniciadas: number; avaliadas: number }[] = []
  for (let i = 0; i < serie.length; i += passo) {
    const parte = serie.slice(i, i + passo)
    const inicio = parte[0].dia
    const fim = parte[parte.length - 1].dia
    grupos.push({
      rotulo: inicio === fim ? inicio.slice(8, 10) + '/' + inicio.slice(5, 7) : `${inicio.slice(8, 10)}/${inicio.slice(5, 7)}–${fim.slice(8, 10)}/${fim.slice(5, 7)}`,
      iniciadas: parte.reduce((soma, item) => soma + item.iniciadas, 0),
      avaliadas: parte.reduce((soma, item) => soma + item.avaliadas, 0)
    })
  }
  const maior = Math.max(1, ...grupos.map((item) => Math.max(item.iniciadas, item.avaliadas)))
  return <section className="panel" style={{ marginTop: 20 }}>
    <div className="panel__heading"><h2>Entrevistas ao longo do tempo</h2><p>Entrevistas iniciadas e avaliadas por intervalo.</p></div>
    <p className="note"><span style={{ color: 'var(--blue)' }}>■</span> Iniciadas　<span style={{ color: 'var(--cyan)' }}>■</span> Avaliadas</p>
    <div style={{ overflowX: 'auto' }}><div role="img" aria-label="Entrevistas por período" style={{ display: 'flex', alignItems: 'end', gap: 13, minWidth: 480, height: 225, borderBottom: '1px solid var(--border)' }}>
      {grupos.map((grupo) => <div key={grupo.rotulo} title={`${grupo.iniciadas} iniciadas; ${grupo.avaliadas} avaliadas`} style={{ flex: '1 0 0', display: 'grid', gridTemplateRows: '1fr auto', height: '100%', gap: 8 }}>
        <div style={{ display: 'flex', alignItems: 'end', justifyContent: 'center', gap: 3, height: 185 }}>
          <div style={{ width: '40%', height: `${grupo.iniciadas / maior * 100}%`, background: 'var(--blue)', borderRadius: '5px 5px 0 0' }} />
          <div style={{ width: '40%', height: `${grupo.avaliadas / maior * 100}%`, background: 'var(--cyan)', borderRadius: '5px 5px 0 0' }} />
        </div>
        <small style={{ fontSize: '.68rem', textAlign: 'center' }}>{grupo.rotulo}</small>
      </div>)}
    </div></div>
    <div className="table-wrap" style={{ marginTop: 16 }}><table>
      <thead><tr><th>Período</th><th>Iniciadas</th><th>Avaliadas</th></tr></thead>
      <tbody>{grupos.map((item) => <tr key={item.rotulo}><td>{item.rotulo}</td><td>{item.iniciadas}</td><td>{item.avaliadas}</td></tr>)}</tbody>
    </table></div>
  </section>
}

export function AdminDashboardPage() {
  const [painel, setPainel] = useState<PainelAdmin | null>(null)
  const [periodo, setPeriodo] = useState('30')
  const [inicio, setInicio] = useState('')
  const [fim, setFim] = useState('')
  const [consulta, setConsulta] = useState('/admin/painel?dias=30')
  const [recarregar, setRecarregar] = useState(0)
  const [loading, setLoading] = useState(true)
  const [erro, setErro] = useState('')
  const [erroFiltro, setErroFiltro] = useState('')
  const [detalheId, setDetalheId] = useState<number | null>(null)
  const [detalhe, setDetalhe] = useState<Detalhe | null>(null)
  const [carregandoDetalhe, setCarregandoDetalhe] = useState(false)
  const [erroDetalhe, setErroDetalhe] = useState('')
  const [avisoDetalhe, setAvisoDetalhe] = useState('')
  const [confirmando, setConfirmando] = useState(false)
  const [reanalisando, setReanalisando] = useState(false)
  const [mostrarErros, setMostrarErros] = useState(false)

  useEffect(() => {
    let ativo = true
    setLoading(true)
    setErro('')
    apiGet<PainelAdmin>(consulta).then((dados) => { if (ativo) setPainel(dados) })
      .catch((falha: unknown) => { if (ativo) setErro(mensagem(falha)) })
      .finally(() => { if (ativo) setLoading(false) })
    return () => { ativo = false }
  }, [consulta, recarregar])

  function aplicarFiltro(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault()
    setErroFiltro('')
    if (periodo === 'personalizado') {
      if (!inicio || !fim) { setErroFiltro('Informe as datas inicial e final.'); return }
      const dias = Math.round((Date.parse(fim) - Date.parse(inicio)) / 86400000) + 1
      if (!Number.isFinite(dias) || dias < 1 || dias > 365) { setErroFiltro('Escolha um período de 1 a 365 dias.'); return }
      setConsulta(`/admin/painel?data_inicio=${inicio}&data_fim=${fim}`)
    } else setConsulta(`/admin/painel?dias=${periodo}`)
    setRecarregar((valor) => valor + 1)
  }

  async function abrirDetalhes(id: number) {
    setDetalheId(id)
    setDetalhe(null)
    setErroDetalhe('')
    setAvisoDetalhe('')
    setConfirmando(false)
    setCarregandoDetalhe(true)
    try { setDetalhe(await apiGet<Detalhe>(`/admin/painel/entrevistas/${id}`)) }
    catch (falha: unknown) { setErroDetalhe(mensagem(falha)) }
    finally { setCarregandoDetalhe(false) }
  }
  function fecharDetalhes() {
    if (reanalisando) return
    setDetalheId(null)
    setDetalhe(null)
    setConfirmando(false)
    setErroDetalhe('')
  }
  async function repetirAnalise() {
    if (!detalhe || !detalhe.pode_solicitar_analise || !confirmando || reanalisando) return
    setReanalisando(true)
    setErroDetalhe('')
    setAvisoDetalhe('')
    try {
      await apiPost<unknown>(`/analise/entrevistas/${detalhe.id}`)
      setAvisoDetalhe('Análise concluída. Os indicadores foram atualizados.')
      setRecarregar((valor) => valor + 1)
    } catch (falha: unknown) {
      if (falha instanceof ApiError && falha.status === 429 && falha.retryAfterSeconds != null) {
        setErroDetalhe(`${falha.message} Aguarde aproximadamente ${Math.ceil(falha.retryAfterSeconds / 60)} minuto(s).`)
      } else setErroDetalhe(mensagem(falha))
    } finally {
      setConfirmando(false)
      try { setDetalhe(await apiGet<Detalhe>(`/admin/painel/entrevistas/${detalhe.id}`)) } catch { /* Preserva a mensagem principal. */ }
      setReanalisando(false)
    }
  }
  const grade = { display: 'grid', gridTemplateColumns: 'repeat(auto-fit,minmax(min(100%,310px),1fr))', gap: 16, marginTop: 16 }

  return <div>
    <div className="page-heading">
      <div><h1>Dashboard administrativo</h1><p>Utilização, avaliações, perguntas e monitoramento da IA.</p></div>
      <button className="button button--outline" type="button" disabled={loading} onClick={() => setRecarregar((n) => n + 1)}><RefreshCw size={16} /> Atualizar dados</button>
    </div>
    <form className="panel" style={{ marginBottom: 20 }} onSubmit={aplicarFiltro}>
      <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', alignItems: 'end' }}>
        <label className="field" style={{ flex: '1 1 210px' }}>Período de análise<select value={periodo} onChange={(evento) => setPeriodo(evento.target.value)}>
          <option value="7">Últimos 7 dias</option><option value="30">Últimos 30 dias</option><option value="90">Últimos 90 dias</option>
          <option value="365">Últimos 365 dias</option><option value="personalizado">Período personalizado</option>
        </select></label>
        {periodo === 'personalizado' && <>
          <label className="field">Data inicial<input type="date" value={inicio} onChange={(evento) => setInicio(evento.target.value)} /></label>
          <label className="field">Data final<input type="date" value={fim} onChange={(evento) => setFim(evento.target.value)} /></label>
        </>}
        <button type="submit" className="button button--primary" disabled={loading}>Aplicar filtro</button>
      </div>
      {erroFiltro && <p role="alert" className="alert alert--error">{erroFiltro}</p>}
      {painel && <p className="note">Período: {painel.periodo_inicio} a {painel.periodo_fim}. Indicadores de situação e cotas são atuais.</p>}
    </form>
    {erro && <section className="panel"><p role="alert" className="alert alert--error">{erro}</p><button type="button" className="button button--outline" onClick={() => setRecarregar((n) => n + 1)}>Tentar novamente</button></section>}
    {loading && !painel && <Loading />}
    {painel && <>
      <h2 style={{ marginBottom: 14 }}>Visão geral das entrevistas</h2>
      <div className="metric-grid metric-grid--4">
        <MetricCard label="Iniciadas no período" value={painel.entrevistas.iniciadas_periodo} icon={<ClipboardList />} />
        <MetricCard label="Avaliadas no período" value={painel.entrevistas.avaliadas_periodo} icon={<CheckCircle2 />} />
        <MetricCard label="Em andamento (total)" value={painel.entrevistas.em_andamento} icon={<Clock3 />} />
        <MetricCard label="Aguardando análise" value={painel.entrevistas.finalizadas_pendentes} icon={<Activity />} />
        <MetricCard label="Em análise (total)" value={painel.entrevistas.em_analise} icon={<BrainCircuit />} />
        <MetricCard label="Erros na análise" value={painel.entrevistas.erro_analise} icon={<AlertTriangle />} />
        <MetricCard label="Nota média no período" value={painel.entrevistas.nota_media_periodo == null ? '—' : `${painel.entrevistas.nota_media_periodo.toFixed(2)}/10`} icon={<BarChart3 />} />
        <MetricCard label="Total de entrevistas" value={painel.entrevistas.total} icon={<MessageSquareText />} />
      </div>
      <h2 style={{ margin: '24px 0 14px' }}>Cadastros</h2>
      <div className="metric-grid metric-grid--5">
        <MetricCard label="Usuários" value={painel.cadastros.usuarios} helper={`${painel.cadastros.usuarios_ativos} ativos`} icon={<Users />} />
        <MetricCard label="Tipos" value={painel.cadastros.tipos} icon={<ClipboardList />} />
        <MetricCard label="Competências" value={painel.cadastros.competencias} icon={<Target />} />
        <MetricCard label="Critérios" value={painel.cadastros.criterios} helper={`Pesos ativos: ${painel.cadastros.soma_pesos_criterios.toFixed(2)}/1,00`} icon={<BarChart3 />} />
        <MetricCard label="Perguntas" value={painel.cadastros.perguntas} helper={`${painel.cadastros.perguntas_ativas} ativas`} icon={<BookOpen />} />
      </div>
      <Grafico serie={painel.serie} />
      <div style={grade}>
        <Distribuicao titulo="Por modalidade" dados={painel.modalidades} />
        <Distribuicao titulo="Por perfil profissional" dados={painel.perfis} nomes={PERFIS} />
        <Distribuicao titulo="Por área técnica" dados={painel.areas} />
      </div>
      <div style={grade}>
        <Medias titulo="Notas médias por modalidade" dados={painel.medias_modalidades} />
        <Medias titulo="Notas médias por área" dados={painel.medias_areas} />
      </div>
      <div style={grade}>
        <section className="panel">
          <div className="panel__heading"><h2>Monitoramento da IA</h2><p>Chamadas diárias em UTC e parâmetros de utilização.</p></div>
          <div className="interview-summary" style={{ marginBottom: 14 }}>
            <div><span>Chamadas hoje</span><strong>{painel.ia.registros_disponiveis ? painel.ia.chamadas_hoje : '—'}</strong></div>
            <div><span>Limite diário</span><strong>{painel.ia.limite_diario}</strong></div>
            <div><span>Entrevistas com erro</span><strong>{painel.ia.erros_analise}</strong></div>
          </div>
          <div className="progress" role="progressbar" aria-label="Consumo da IA" aria-valuemin={0} aria-valuemax={100} aria-valuenow={painel.ia.percentual}>
            <div style={{ width: `${Math.max(0, Math.min(100, painel.ia.percentual))}%` }} />
          </div>
          <p className="note">{painel.ia.registros_disponiveis ? `${painel.ia.percentual.toFixed(1)}% da cota diária utilizada.` : 'O consumo ainda não pode ser confirmado.'} Custos monetários não estão registrados.</p>
          <ConfiguracaoIA aoSalvar={() => setRecarregar((n) => n + 1)} />
        </section>
        <section className="panel">
          <div className="panel__heading"><h2>Qualidade das perguntas</h2><p>Disponibilidade para os perfis profissionais.</p></div>
          <div className="interview-summary"><div><span>Ativas</span><strong>{painel.cadastros.perguntas_ativas}</strong></div>
            <div><span>Inativas</span><strong>{painel.cadastros.perguntas_inativas}</strong></div>
            <div><span>Sem referência</span><strong>{painel.cadastros.sem_referencia}</strong></div>
          </div>
          <p className="note">Cobertura do seletor: {painel.cobertura.contextos_prontos}/{painel.cobertura.total_contextos} combinações prontas.</p>
          <div className="progress" role="progressbar" aria-label="Cobertura das perguntas" aria-valuemin={0} aria-valuemax={painel.cobertura.total_contextos} aria-valuenow={painel.cobertura.contextos_prontos}>
            <div style={{ width: `${painel.cobertura.total_contextos ? 100 * painel.cobertura.contextos_prontos / painel.cobertura.total_contextos : 0}%` }} />
          </div>
          <Link className="button button--outline" to="/admin/perguntas" style={{ marginTop: 16 }}>Gerenciar perguntas</Link>
        </section>
      </div>
      <div style={grade}><Distribuicao titulo="Perguntas ativas por dificuldade" dados={painel.dificuldades} nomes={DIFICULDADES} />
        <Distribuicao titulo="Perguntas ativas por tipo" dados={painel.perguntas_por_tipo} /></div>
      <section className="panel" style={{ marginTop: 20 }}>
        <div className="panel__heading"><h2>Alertas administrativos</h2><p>Ocorrências verificadas a partir dos registros atuais.</p></div>
        {painel.alertas.length === 0 ? <p className="note">Nenhum alerta nas verificações disponíveis.</p> : painel.alertas.map((alerta, i) => <div key={`${alerta.titulo}-${i}`} role="status" style={{ padding: 12, marginBottom: 10, border: '1px solid var(--border)', borderLeft: `4px solid ${alerta.gravidade === 'alta' ? 'var(--danger)' : alerta.gravidade === 'media' ? 'var(--warning)' : 'var(--blue)'}`, borderRadius: 10 }}>
          <strong>{alerta.titulo}</strong><p style={{ margin: '4px 0 0' }}>{alerta.detalhe}</p>
        </div>)}
        {painel.entrevistas.erro_analise > 0 && <div style={{ marginTop: 15 }}>
          <button type="button" className="button button--outline" onClick={() => setMostrarErros((v) => !v)}>{mostrarErros ? 'Ocultar entrevistas com erro' : 'Ver entrevistas com erro'}</button>
          {mostrarErros && <div className="table-wrap" style={{ marginTop: 12 }}><table>
            <thead><tr><th>ID</th><th>Estudante</th><th>Modalidade</th><th>Início</th><th>Ação</th></tr></thead>
            <tbody>{painel.entrevistas_com_erro.map((item) => <tr key={item.id}>
              <td>#{item.id}</td><td>{item.estudante}</td><td>{item.modalidade}</td><td>{dataBrasileira(item.data_inicio)}</td>
              <td><button type="button" className="button button--small button--outline" onClick={() => void abrirDetalhes(item.id)}>Investigar</button></td>
            </tr>)}</tbody>
          </table></div>}
        </div>}
        {painel.cobertura.total_pendentes > 0 && <details style={{ marginTop: 15 }}>
          <summary>Ver {painel.cobertura.total_pendentes} combinações sem cobertura</summary>
          <div className="table-wrap"><table><thead><tr><th>Tipo</th><th>Área/subárea</th><th>Perfil</th><th>Problema</th></tr></thead>
            <tbody>{painel.cobertura.pendentes.map((item, i) => <tr key={i}><td>{item.tipo}</td><td>{[item.area, item.subarea].filter(Boolean).join(' / ') || '—'}</td><td>{PERFIS[item.perfil]}</td><td>{item.motivo}</td></tr>)}</tbody>
          </table></div>
        </details>}
      </section>
      <AdminEntrevistasLista recentes={painel.recentes} total={painel.entrevistas.total} atualizar={recarregar} onDetalhes={(id) => void abrirDetalhes(id)} />
      <section className="panel" style={{ marginTop: 20 }}>
        <h2>Ações rápidas</h2>
        <div className="button-row" style={{ flexWrap: 'wrap', marginTop: 12 }}>
          <Link className="button button--primary" to="/admin/usuarios">Cadastrar usuário</Link>
          <Link className="button button--outline" to="/admin/perguntas">Gerenciar perguntas</Link>
          <Link className="button button--outline" to="/admin/criterios">Revisar critérios</Link>
          <Link className="button button--outline" to="/admin/tipos">Tipos de entrevista</Link>
        </div>
      </section>
    </>}
    {detalheId !== null && <div role="presentation" style={{ position: 'fixed', inset: 0, zIndex: 1200, background: 'rgba(10,25,60,.65)', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 16 }}>
      <section role="dialog" aria-modal="true" aria-labelledby="titulo-detalhe" className="panel" style={{ width: '100%', maxWidth: 680, maxHeight: '90vh', overflowY: 'auto', background: 'white' }}>
        <div className="panel__heading panel__heading--actions"><div><h2 id="titulo-detalhe">Entrevista #{detalheId}</h2><p>Diagnóstico sem conteúdo das respostas.</p></div>
          <button type="button" className="button button--outline" disabled={reanalisando} onClick={fecharDetalhes}>Fechar</button></div>
        {carregandoDetalhe && <Loading />}
        {detalhe && <>
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
          <p className="note">Início: {dataBrasileira(detalhe.data_inicio)}. {detalhe.perfil_profissional ? `${detalhe.perguntas} perguntas selecionadas.` : 'Entrevista antiga (legada).'}</p>
          {detalhe.status === 'erro_analise' && <p className="note">A causa original não foi armazenada. Confira os logs do servidor antes de repetir.</p>}
          {detalhe.orientacoes.length > 0 && <ul>{detalhe.orientacoes.map((item, i) => <li key={i}>{item}</li>)}</ul>}
          {detalhe.pode_solicitar_analise && <div style={{ marginTop: 16 }}>
            {!confirmando ? <button type="button" className="button button--primary" onClick={() => setConfirmando(true)}>Solicitar nova análise</button> : <div style={{ border: '1px solid var(--border)', padding: 12, borderRadius: 10 }}>
              <p>Nova análise pode consumir chamadas reais e gerar custos. Confirme somente após verificar a configuração da IA.</p>
              <div className="button-row"><button type="button" className="button button--outline" disabled={reanalisando} onClick={() => setConfirmando(false)}>Cancelar</button>
                <button type="button" className="button button--primary" disabled={reanalisando} onClick={() => void repetirAnalise()}>{reanalisando ? 'Analisando...' : 'Confirmar nova tentativa'}</button></div>
            </div>}
          </div>}
          {detalhe.status === 'erro_analise' && !detalhe.pode_solicitar_analise && <p className="alert alert--error">Esta entrevista não atende às condições de reanálise.</p>}
        </>}
        {erroDetalhe && <p className="alert alert--error" role="alert">{erroDetalhe}</p>}
        {avisoDetalhe && <p className="note" role="status">{avisoDetalhe}</p>}
      </section>
    </div>}
  </div>
}
