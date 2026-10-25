
import { useEffect, useMemo, useState } from 'react'
import { BarChart3, CheckCircle2, FileText, Star } from 'lucide-react'
import { Link } from 'react-router-dom'
import { Loading } from '../components/Loading'
import { MetricCard } from '../components/MetricCard'
import { studentService } from '../services/studentService'
import type { EvolucaoCriterios, EvolucaoPontuacao, ItemHistorico, ResumoHistorico } from '../types/historico'

const NOMES_STATUS: Record<ItemHistorico['status'], string> = {
  em_andamento: 'Em andamento', finalizada: 'Finalizada', em_analise: 'Em análise',
  avaliada: 'Avaliada', erro_analise: 'Erro na análise', cancelada: 'Cancelada'
}

function formatarData(valor: string): string {
  // Datas do SQLite sem fuso são horários locais, não UTC.
  const data = new Date(valor.includes('T') ? valor : valor.replace(' ', 'T'))
  return Number.isNaN(data.getTime()) ? valor : data.toLocaleDateString('pt-BR')
}

export function DashboardPage() {
  const [resumo, setResumo] = useState<ResumoHistorico | null>(null)
  const [historico, setHistorico] = useState<ItemHistorico[]>([])
  const [evolucao, setEvolucao] = useState<EvolucaoPontuacao[]>([])
  const [evolucaoCriterios, setEvolucaoCriterios] = useState<EvolucaoCriterios[]>([])
  const [loading, setLoading] = useState(true)
  const [erro, setErro] = useState('')
  const [erroCriterios, setErroCriterios] = useState('')
  const [tentativa, setTentativa] = useState(0)
  const [tipoFiltro, setTipoFiltro] = useState('todos')

  useEffect(() => {
    let ativo = true
    setLoading(true)
    setErro('')
    setErroCriterios('')
    setResumo(null)
    setHistorico([])
    setEvolucao([])
    setEvolucaoCriterios([])

    // Uma falha nos critérios não deve ocultar o resumo e as notas já publicados.
    Promise.allSettled([
      studentService.resumo(), studentService.historico(),
      studentService.evolucao(), studentService.evolucaoCriterios()
    ])
      .then(([resultadoResumo, resultadoHistorico, resultadoEvolucao, resultadoCriterios]) => {
        if (!ativo) return
        if (resultadoResumo.status === 'rejected') throw resultadoResumo.reason
        if (resultadoHistorico.status === 'rejected') throw resultadoHistorico.reason
        if (resultadoEvolucao.status === 'rejected') throw resultadoEvolucao.reason
        setResumo(resultadoResumo.value)
        setHistorico(resultadoHistorico.value)
        setEvolucao(resultadoEvolucao.value.filter((item) => Number.isFinite(item.pontuacao) && item.pontuacao >= 0 && item.pontuacao <= 10))
        if (resultadoCriterios.status === 'fulfilled') setEvolucaoCriterios(resultadoCriterios.value)
        else setErroCriterios(resultadoCriterios.reason instanceof Error ? resultadoCriterios.reason.message : 'Não foi possível consultar os critérios.')
      })
      .catch((falha: unknown) => {
        if (ativo) setErro(falha instanceof Error ? falha.message : 'Erro ao carregar os indicadores.')
      })
      .finally(() => { if (ativo) setLoading(false) })

    return () => { ativo = false }
  }, [tentativa])

  const tipos = useMemo(() => {
    const unicos = new Map<number, string>()
    historico.forEach((item) => {
      unicos.set(item.tipo_entrevista_id, item.tipo_entrevista ?? `Tipo ${item.tipo_entrevista_id}`)
    })
    return [...unicos].sort((a, b) => a[1].localeCompare(b[1], 'pt-BR'))
  }, [historico])

  const evolucaoFiltrada = useMemo(() =>
    evolucao.filter((item) => tipoFiltro === 'todos' || item.tipo_entrevista_id === Number(tipoFiltro)),
    [evolucao, tipoFiltro]
  )

  const criteriosFiltrados = useMemo(() =>
    evolucaoCriterios.filter((item) => tipoFiltro === 'todos' || item.tipo_entrevista_id === Number(tipoFiltro)),
    [evolucaoCriterios, tipoFiltro]
  )

  const ultimasNotas = evolucaoFiltrada.slice(-12)
  const criteriosRecentes = criteriosFiltrados.length
    ? criteriosFiltrados[criteriosFiltrados.length - 1].criterios
    : []

  const ultima = evolucaoFiltrada[evolucaoFiltrada.length - 1]
  const primeira = evolucaoFiltrada[0]

  const mediaFiltrada = evolucaoFiltrada.length
    ? evolucaoFiltrada.reduce((soma, item) => soma + item.pontuacao, 0) / evolucaoFiltrada.length
    : null

  const ultimas = useMemo(() => historico.slice(0, 5), [historico])

  if (loading) return <Loading />

  if (erro) return (
    <section className="panel">
      <h1>Dashboard indisponível</h1>
      <p role="alert" className="alert alert--error">{erro}</p>
      <button className="button button--primary" type="button" onClick={() => setTentativa((valor) => valor + 1)}>
        Tentar novamente
      </button>
    </section>
  )

  return (
    <div>
      <div className="page-heading">
        <div>
          <h1>Dashboard</h1>
          <p>Acompanhe os resultados das suas entrevistas ao longo do tempo.</p>
        </div>
      </div>

      <div className="metric-grid metric-grid--4">
        <MetricCard label="Entrevistas realizadas" value={resumo?.quantidade_total ?? 0} icon={<FileText />} />
        <MetricCard label="Entrevistas avaliadas" value={resumo?.quantidade_avaliada ?? 0} icon={<CheckCircle2 />} />
        <MetricCard label="Média geral (0 a 10)" value={resumo?.media_pontuacoes?.toFixed(2) ?? '-'} icon={<BarChart3 />} />
        <MetricCard label="Última pontuação" value={resumo?.ultima_pontuacao?.toFixed(2) ?? '-'} icon={<Star />} />
      </div>

      <section className="panel">
        <div className="panel__heading">
          <h2>Evolução por modalidade</h2>
          <p>Selecione uma modalidade para comparar avaliações equivalentes. As notas são exibidas em ordem cronológica.</p>
        </div>

        <label className="field" style={{ maxWidth: 430, marginBottom: '1rem' }}>
          Modalidade
          <select value={tipoFiltro} onChange={(evento) => setTipoFiltro(evento.target.value)}>
            <option value="todos">Todas as modalidades (visão geral)</option>
            {tipos.map(([id, nome]) => <option key={id} value={id}>{nome}</option>)}
          </select>
        </label>

        <div className="interview-summary">
          <div>
            <span>Avaliações selecionadas</span>
            <strong>{evolucaoFiltrada.length}</strong>
          </div>
          <div>
            <span>Média selecionada</span>
            <strong>{mediaFiltrada === null ? '-' : `${mediaFiltrada.toFixed(2)}/10`}</strong>
          </div>
          <div>
            <span>Variação primeira → última</span>
            <strong>
              {primeira && ultima && evolucaoFiltrada.length >= 2
                ? `${ultima.pontuacao - primeira.pontuacao > 0 ? '+' : ''}${(ultima.pontuacao - primeira.pontuacao).toFixed(2)} ponto(s)`
                : '-'}
            </strong>
          </div>
        </div>

        {ultimasNotas.length === 0 ? (
          <div className="empty-state">Nenhuma entrevista avaliada nesta modalidade.</div>
        ) : (
          <div
            className="mini-chart"
            role="group"
            aria-label="Últimas pontuações avaliadas em ordem cronológica"
            style={{ marginTop: '1rem' }}
          >
            {ultimasNotas.map((item) => (
              <div
                className="mini-chart__item"
                key={item.entrevista_id}
                title={`Entrevista #${item.entrevista_id} — ${formatarData(item.data)} — ${item.pontuacao.toFixed(2)}/10`}
              >
                <strong style={{ fontSize: '.8rem' }}>{item.pontuacao.toFixed(1)}</strong>
                <div
                  className="mini-chart__bar"
                  style={{ height: `${Math.max(2, Math.min(100, item.pontuacao * 10))}%` }}
                />
                <Link to={`/relatorios/${item.entrevista_id}`} style={{ fontSize: '.75rem' }}>
                  #{item.entrevista_id}
                </Link>
              </div>
            ))}
          </div>
        )}

        {evolucaoFiltrada.length > 12 && (
          <p className="note">
            O gráfico mostra as últimas 12 avaliações da seleção.
            A média considera todas as avaliações selecionadas.
          </p>
        )}

        {tipoFiltro === 'todos' && evolucaoFiltrada.length > 1 && (
          <p className="note">
            Entrevistas de modalidades diferentes podem avaliar habilidades distintas.
            Use o filtro para uma comparação mais consistente.
          </p>
        )}
      </section>

      <section className="panel">
        <div className="panel__heading">
          <h2>Critérios da avaliação mais recente</h2>
          <p>Critérios e médias da última entrevista avaliada dentro do filtro de modalidade.</p>
        </div>

        {erroCriterios ? (
          <div role="alert">
            <p className="alert alert--error">Não foi possível consultar a evolução dos critérios: {erroCriterios}</p>
            <button type="button" className="button button--outline" onClick={() => setTentativa((valor) => valor + 1)}>Tentar novamente</button>
          </div>
        ) : criteriosRecentes.length === 0 ? (
          <div className="empty-state">Ainda não há critérios avaliados para esta modalidade.</div>
        ) : (
          <div className="progress-list">
            {criteriosRecentes.map((item) => (
              <div className="progress-row" key={item.criterio_id}>
                <span title={item.criterio_descricao ?? undefined}>{item.criterio}</span>
                <div
                  className="progress"
                  role="progressbar"
                  aria-label={item.criterio}
                  aria-valuemin={0}
                  aria-valuemax={10}
                  aria-valuenow={item.media}
                >
                  <div style={{ width: `${Math.max(0, Math.min(100, item.media * 10))}%` }} />
                </div>
                <strong>{item.media.toFixed(1)}</strong>
              </div>
            ))}
          </div>
        )}
      </section>

      <section className="panel">
        <div className="panel__heading panel__heading--actions">
          <div>
            <h2>Últimas entrevistas</h2>
            <p>Retome uma entrevista ou consulte um relatório já liberado.</p>
          </div>
          <div className="button-row">
            <Link className="button button--primary" to="/entrevistas/nova">Nova entrevista</Link>
            <Link className="button button--outline" to="/historico">Histórico completo</Link>
          </div>
        </div>

        {ultimas.length === 0 ? (
          <div className="empty-state">Você ainda não iniciou nenhuma entrevista.</div>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Modalidade</th>
                  <th>Data</th>
                  <th>Situação</th>
                  <th>Nota</th>
                  <th>Ação</th>
                </tr>
              </thead>
              <tbody>
                {ultimas.map((item) => (
                  <tr key={item.id}>
                    <td>#{item.id}</td>
                    <td>
                      {item.tipo_entrevista ?? `Tipo ${item.tipo_entrevista_id}`}
                      {item.area_tecnica && (
                        <div>
                          <small>
                            {item.area_tecnica}
                            {item.subarea_tecnica ? ` / ${item.subarea_tecnica}` : ''}
                          </small>
                        </div>
                      )}
                    </td>
                    <td>{formatarData(item.data_inicio)}</td>
                    <td>
                      <span className={`status status--${item.status}`}>{NOMES_STATUS[item.status]}</span>
                    </td>
                    <td>
                      {item.status === 'avaliada' && item.pontuacao_final !== null
                        ? item.pontuacao_final.toFixed(2)
                        : '-'}
                    </td>
                    <td>
                      {item.status === 'avaliada' ? (
                        <Link to={`/relatorios/${item.id}`}>Relatório</Link>
                      ) : item.status === 'cancelada' ? '-' : (
                        <Link to={`/entrevistas/${item.id}`}>Ver entrevista</Link>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  )
}
