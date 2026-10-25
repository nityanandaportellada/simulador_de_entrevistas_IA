
import { useEffect, useMemo, useState } from 'react'
import { BarChart3, CheckCircle2, FileText, Star, TimerReset } from 'lucide-react'
import { Link } from 'react-router-dom'
import { Loading } from '../components/Loading'
import { MetricCard } from '../components/MetricCard'
import { studentService } from '../services/studentService'
import type { EvolucaoCriterios, ItemHistorico, ResumoHistorico } from '../types/historico'

const SITUACOES: Record<ItemHistorico['status'], string> = {
  em_andamento: 'Em andamento', finalizada: 'Finalizada', em_analise: 'Em análise',
  avaliada: 'Avaliada', erro_analise: 'Erro na análise', cancelada: 'Cancelada'
}

function formatarData(valor: string): string {
  // Datas sem fuso no SQLite são horários locais, não UTC.
  const data = new Date(valor.includes('T') ? valor : valor.replace(' ', 'T'))
  return Number.isNaN(data.getTime()) ? valor : data.toLocaleString('pt-BR')
}

function formatarNota(valor: number | null | undefined): string {
  return valor === null || valor === undefined || !Number.isFinite(valor) ? '-' : valor.toFixed(2)
}

function mensagemErro(erro: unknown): string {
  return erro instanceof Error ? erro.message : 'Não foi possível carregar o histórico.'
}

export function HistoricoPage() {
  const [resumo, setResumo] = useState<ResumoHistorico | null>(null)
  const [historico, setHistorico] = useState<ItemHistorico[]>([])
  const [evolucaoCriterios, setEvolucaoCriterios] = useState<EvolucaoCriterios[]>([])
  const [loading, setLoading] = useState(true)
  const [erro, setErro] = useState('')
  const [erroCriterios, setErroCriterios] = useState('')
  const [tentativa, setTentativa] = useState(0)
  const [tipoFiltro, setTipoFiltro] = useState('todos')
  const [statusFiltro, setStatusFiltro] = useState('todos')
  const [busca, setBusca] = useState('')
  const [primeiroId, setPrimeiroId] = useState('')
  const [segundoId, setSegundoId] = useState('')

  // Consulta apenas dados do usuário autenticado, já filtrados no backend.
  useEffect(() => {
    let ativo = true
    setLoading(true)
    setErro('')
    setErroCriterios('')
    setResumo(null)
    setHistorico([])
    setEvolucaoCriterios([])
    // O histórico permanece acessível se apenas a evolução por critérios falhar.
    Promise.allSettled([studentService.resumo(), studentService.historico(), studentService.evolucaoCriterios()])
      .then(([resultadoResumo, resultadoHistorico, resultadoCriterios]) => {
        if (!ativo) return
        if (resultadoResumo.status === 'rejected') throw resultadoResumo.reason
        if (resultadoHistorico.status === 'rejected') throw resultadoHistorico.reason
        setResumo(resultadoResumo.value)
        setHistorico(resultadoHistorico.value)
        if (resultadoCriterios.status === 'fulfilled') setEvolucaoCriterios(resultadoCriterios.value)
        else setErroCriterios(mensagemErro(resultadoCriterios.reason))
      })
      .catch((falha: unknown) => { if (ativo) setErro(mensagemErro(falha)) })
      .finally(() => { if (ativo) setLoading(false) })
    return () => { ativo = false }
  }, [tentativa])

  const tipos = useMemo(() => {
    const unicos = new Map<number, string>()
    historico.forEach((item) => unicos.set(item.tipo_entrevista_id, item.tipo_entrevista ?? `Tipo ${item.tipo_entrevista_id}`))
    return [...unicos].sort((a, b) => a[1].localeCompare(b[1], 'pt-BR'))
  }, [historico])

  const filtradas = useMemo(() => historico.filter((item) => {
    if (tipoFiltro !== 'todos' && item.tipo_entrevista_id !== Number(tipoFiltro)) return false
    if (statusFiltro !== 'todos' && item.status !== statusFiltro) return false
    const termo = busca.trim().toLocaleLowerCase('pt-BR')
    const conteudo = `${item.id} ${item.tipo_entrevista ?? ''} ${item.area_tecnica ?? ''} ${item.subarea_tecnica ?? ''}`.toLocaleLowerCase('pt-BR')
    return !termo || conteudo.includes(termo)
  }), [historico, tipoFiltro, statusFiltro, busca])

  const avaliadas = useMemo(() => historico.filter((item) => item.status === 'avaliada' && item.pontuacao_final !== null && Number.isFinite(item.pontuacao_final)), [historico])
  const primeira = avaliadas.find((item) => String(item.id) === primeiroId)

  // Compara somente a mesma modalidade e, para técnicas, a mesma área e subárea.
  const comparaveis = avaliadas.filter((item) => primeira && item.id !== primeira.id &&
    item.tipo_entrevista_id === primeira.tipo_entrevista_id &&
    item.area_tecnica_id === primeira.area_tecnica_id &&
    item.subarea_tecnica_id === primeira.subarea_tecnica_id)

  const segunda = comparaveis.find((item) => String(item.id) === segundoId)
  const detalhesPrimeira = evolucaoCriterios.find((item) => item.entrevista_id === primeira?.id)
  const detalhesSegunda = evolucaoCriterios.find((item) => item.entrevista_id === segunda?.id)

  const criteriosComparados = (detalhesPrimeira?.criterios ?? []).flatMap((criterio) => {
    const correspondente = detalhesSegunda?.criterios.find((outro) => outro.criterio_id === criterio.criterio_id)
    return correspondente ? [{ id: criterio.criterio_id, nome: criterio.criterio, antes: criterio.media, depois: correspondente.media }] : []
  })

  if (loading) return <Loading />

  if (erro) return (
    <section className="panel">
      <h1>Histórico indisponível</h1>
      <p className="alert alert--error" role="alert">{erro}</p>
      <button className="button button--primary" type="button" onClick={() => setTentativa((valor) => valor + 1)}>
        Tentar novamente
      </button>
    </section>
  )

  return (
    <div>
      <div className="page-heading">
        <div>
          <h1>Histórico</h1>
          <p>Consulte suas entrevistas e compare resultados de avaliações concluídas.</p>
        </div>
        <Link className="button button--primary" to="/entrevistas/nova">Nova entrevista</Link>
      </div>

      <div className="metric-grid metric-grid--5">
        <MetricCard label="Total" value={resumo?.quantidade_total ?? 0} icon={<FileText />} />
        <MetricCard label="Avaliadas" value={resumo?.quantidade_avaliada ?? 0} icon={<CheckCircle2 />} />
        <MetricCard label="Média geral" value={formatarNota(resumo?.media_pontuacoes)} icon={<BarChart3 />} />
        <MetricCard label="Melhor nota" value={formatarNota(resumo?.melhor_pontuacao)} icon={<Star />} />
        <MetricCard label="Última nota" value={formatarNota(resumo?.ultima_pontuacao)} icon={<TimerReset />} />
      </div>

      <section className="panel">
        <div className="panel__heading">
          <h2>Entrevistas realizadas</h2>
          <p>Filtre por modalidade, situação ou termo de pesquisa.</p>
        </div>

        <div className="two-column" style={{ marginBottom: '1rem' }}>
          <label className="field">
            Modalidade
            <select value={tipoFiltro} onChange={(evento) => setTipoFiltro(evento.target.value)}>
              <option value="todos">Todas as modalidades</option>
              {tipos.map(([id, nome]) => <option key={id} value={id}>{nome}</option>)}
            </select>
          </label>

          <label className="field">
            Situação
            <select value={statusFiltro} onChange={(evento) => setStatusFiltro(evento.target.value)}>
              <option value="todos">Todas as situações</option>
              {Object.entries(SITUACOES).map(([codigo, nome]) => (
                <option key={codigo} value={codigo}>{nome}</option>
              ))}
            </select>
          </label>

          <label className="field">
            Pesquisar por número, tipo ou área
            <input
              value={busca}
              onChange={(evento) => setBusca(evento.target.value)}
              placeholder="Ex.: 12, Tecnologia, Liderança"
            />
          </label>
        </div>

        <p className="note">
          Exibindo {filtradas.length} de {historico.length} entrevistas.
          As médias gerais acima consideram todo o histórico avaliado.
        </p>

        {filtradas.length === 0 ? (
          <div className="empty-state">Nenhuma entrevista corresponde aos filtros selecionados.</div>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Entrevista</th>
                  <th>Modalidade</th>
                  <th>Área / subárea</th>
                  <th>Data</th>
                  <th>Situação</th>
                  <th>Nota</th>
                  <th>Ação</th>
                </tr>
              </thead>
              <tbody>
                {filtradas.map((item) => (
                  <tr key={item.id}>
                    <td>#{item.id}</td>
                    <td>{item.tipo_entrevista ?? `Tipo ${item.tipo_entrevista_id}`}</td>
                    <td>
                      {item.area_tecnica
                        ? `${item.area_tecnica}${item.subarea_tecnica ? ` / ${item.subarea_tecnica}` : ''}`
                        : '-'}
                    </td>
                    <td>{formatarData(item.data_inicio)}</td>
                    <td>
                      <span className={`status status--${item.status}`}>{SITUACOES[item.status]}</span>
                    </td>
                    <td>{item.status === 'avaliada' ? formatarNota(item.pontuacao_final) : '-'}</td>
                    <td>
                      {item.status === 'avaliada' ? (
                        <Link to={`/relatorios/${item.id}`}>Ver relatório</Link>
                      ) : item.status === 'cancelada' ? '-' : (
                        <Link to={`/entrevistas/${item.id}`}>
                          {item.status === 'em_andamento' ? 'Continuar' : 'Ver situação'}
                        </Link>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section className="panel">
        <div className="panel__heading">
          <h2>Comparar duas entrevistas</h2>
          <p>Selecione primeiro a entrevista inicial e depois outra do mesmo tipo e contexto técnico.</p>
        </div>

        <div className="two-column">
          <label className="field">
            Primeira entrevista
            <select
              value={primeiroId}
              onChange={(evento) => { setPrimeiroId(evento.target.value); setSegundoId('') }}
            >
              <option value="">Selecione uma entrevista avaliada</option>
              {avaliadas.map((item) => (
                <option key={item.id} value={item.id}>
                  #{item.id} — {item.tipo_entrevista ?? `Tipo ${item.tipo_entrevista_id}`} — {formatarNota(item.pontuacao_final)}
                </option>
              ))}
            </select>
          </label>

          <label className="field">
            Segunda entrevista
            <select
              value={segundoId}
              disabled={!primeira}
              onChange={(evento) => setSegundoId(evento.target.value)}
            >
              <option value="">Selecione uma entrevista comparável</option>
              {comparaveis.map((item) => (
                <option key={item.id} value={item.id}>
                  #{item.id} — {formatarNota(item.pontuacao_final)} — {formatarData(item.data_inicio)}
                </option>
              ))}
            </select>
          </label>
        </div>

        {primeira && comparaveis.length === 0 && (
          <p className="note" style={{ marginTop: '1rem' }}>
            Ainda não existe uma segunda entrevista avaliada com a mesma modalidade, área e subárea.
          </p>
        )}

        {primeira && segunda && primeira.pontuacao_final !== null && segunda.pontuacao_final !== null && (
          <div style={{ marginTop: '1.25rem' }}>
            <div className="interview-summary">
              <div>
                <span>Primeira entrevista</span>
                <strong>#{primeira.id}: {formatarNota(primeira.pontuacao_final)}</strong>
              </div>
              <div>
                <span>Segunda entrevista</span>
                <strong>#{segunda.id}: {formatarNota(segunda.pontuacao_final)}</strong>
              </div>
              <div>
                <span>Variação (segunda − primeira)</span>
                <strong>
                  {(segunda.pontuacao_final - primeira.pontuacao_final) > 0 ? '+' : ''}
                  {(segunda.pontuacao_final - primeira.pontuacao_final).toFixed(2)} ponto(s)
                </strong>
              </div>
            </div>

            <p className="note">
              A diferença indica variação entre estas duas avaliações, não necessariamente melhoria ao longo do tempo.
              Para evolução cronológica, use o Dashboard.
            </p>

            {erroCriterios && (
              <div role="alert">
                <p className="alert alert--error">Não foi possível comparar os critérios: {erroCriterios}. As notas gerais continuam disponíveis.</p>
                <button type="button" className="button button--outline" onClick={() => setTentativa((valor) => valor + 1)}>Tentar novamente</button>
              </div>
            )}
            {!erroCriterios && criteriosComparados.length === 0 && (
              <p className="note">As entrevistas selecionadas não possuem critérios em comum para comparação.</p>
            )}
            {!erroCriterios && criteriosComparados.length > 0 && (
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>Critério comum</th>
                      <th>Primeira</th>
                      <th>Segunda</th>
                      <th>Diferença</th>
                    </tr>
                  </thead>
                  <tbody>
                    {criteriosComparados.map((criterio) => (
                      <tr key={criterio.id}>
                        <td>{criterio.nome}</td>
                        <td>{criterio.antes.toFixed(2)}</td>
                        <td>{criterio.depois.toFixed(2)}</td>
                        <td>
                          {criterio.depois - criterio.antes > 0 ? '+' : ''}
                          {(criterio.depois - criterio.antes).toFixed(2)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            <div className="button-row" style={{ marginTop: '1rem' }}>
              <Link className="button button--outline" to={`/relatorios/${primeira.id}`}>
                Relatório #{primeira.id}
              </Link>
              <Link className="button button--outline" to={`/relatorios/${segunda.id}`}>
                Relatório #{segunda.id}
              </Link>
            </div>
          </div>
        )}
      </section>
    </div>
  )
}
