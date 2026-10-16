import { useEffect, useMemo, useState } from 'react'
import { BarChart3, CheckCircle2, FileText, Star } from 'lucide-react'
import { Link } from 'react-router-dom'
import { Loading } from '../components/Loading'
import { MetricCard } from '../components/MetricCard'
import { studentService } from '../services/studentService'
import type { EvolucaoPontuacao, ItemHistorico, ResumoHistorico } from '../types/historico'

export function DashboardPage() {
  const [resumo, setResumo] = useState<ResumoHistorico | null>(null)
  const [historico, setHistorico] = useState<ItemHistorico[]>([])
  const [evolucao, setEvolucao] = useState<EvolucaoPontuacao[]>([])
  const [criterios, setCriterios] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([
      studentService.resumo(),
      studentService.historico(),
      studentService.evolucao(),
      studentService.evolucaoCriterios()
    ])
      .then(([r, h, e, c]) => {
        setResumo(r)
        setHistorico(h)
        setEvolucao(e)
        setCriterios(c)
      })
      .finally(() => setLoading(false))
  }, [])

  const ultimas = useMemo(() => historico.slice(0, 5), [historico])

  if (loading) return <Loading />

  const criterioRows = Array.isArray(criterios)
    ? criterios.slice(0, 5)
    : []

  return (
    <div>
      <div className="page-heading">
        <div>
          <h1>Dashboard</h1>
          <p>Acompanhe seu desempenho no simulador de entrevistas.</p>
        </div>
      </div>

      <div className="metric-grid metric-grid--4">
        <MetricCard label="Entrevistas realizadas" value={resumo?.quantidade_total ?? 0} icon={<FileText />} />
        <MetricCard label="Entrevistas avaliadas" value={resumo?.quantidade_avaliada ?? 0} icon={<CheckCircle2 />} />
        <MetricCard label="Média das pontuações" value={resumo?.media_pontuacoes?.toFixed(2) ?? '-'} icon={<BarChart3 />} />
        <MetricCard label="Última pontuação" value={resumo?.ultima_pontuacao?.toFixed(2) ?? '-'} icon={<Star />} />
      </div>

      <div className="two-column">
        <section className="panel">
          <div className="panel__heading">
            <div>
              <h2>Evolução das pontuações</h2>
              <p>Últimas entrevistas avaliadas.</p>
            </div>
          </div>
          <div className="mini-chart">
            {evolucao.length === 0 ? (
              <div className="empty-state">Ainda não há evolução disponível.</div>
            ) : (
              evolucao.map((item, index) => (
                <div className="mini-chart__item" key={item.entrevista_id}>
                  <div className="mini-chart__bar" style={{ height: `${Math.max(12, item.pontuacao * 9)}%` }} />
                  <span>{index + 1}</span>
                </div>
              ))
            )}
          </div>
        </section>

        <section className="panel">
          <div className="panel__heading">
            <div>
              <h2>Desempenho por critérios</h2>
              <p>Média dos critérios disponíveis no histórico.</p>
            </div>
          </div>

          {criterioRows.length > 0 ? (
            <div className="progress-list">
              {criterioRows.map((item: any, index: number) => (
                <div key={item.criterio_id ?? index} className="progress-row">
                  <span>{item.criterio ?? `Critério ${index + 1}`}</span>
                  <div className="progress"><div style={{ width: `${Math.min(100, Number(item.media ?? 0) * 10)}%` }} /></div>
                  <strong>{Number(item.media ?? 0).toFixed(1)}</strong>
                </div>
              ))}
            </div>
          ) : (
            <div className="empty-state">Os critérios aparecerão após as primeiras avaliações.</div>
          )}
        </section>
      </div>

      <section className="panel">
        <div className="panel__heading panel__heading--actions">
          <div>
            <h2>Últimas entrevistas</h2>
            <p>Suas entrevistas mais recentes no simulador.</p>
          </div>
          <div className="button-row">
            <Link className="button button--primary" to="/entrevistas/nova">Iniciar nova entrevista</Link>
            <Link className="button button--outline" to="/historico">Ver histórico</Link>
          </div>
        </div>

        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>ID</th>
                <th>Tipo</th>
                <th>Data</th>
                <th>Status</th>
                <th>Pontuação</th>
                <th />
              </tr>
            </thead>
            <tbody>
              {ultimas.map((item) => (
                <tr key={item.id}>
                  <td>#{item.id}</td>
                  <td>Tipo {item.tipo_entrevista_id}</td>
                  <td>{item.data_inicio}</td>
                  <td><span className={`status status--${item.status}`}>{item.status}</span></td>
                  <td>{item.pontuacao_final ?? '-'}</td>
                  <td>
                    {item.status === 'avaliada' && (
                      <Link to={`/relatorios/${item.id}`}>Ver detalhes</Link>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  )
}
