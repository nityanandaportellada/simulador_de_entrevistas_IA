import { useEffect, useState } from 'react'
import { BarChart3, CheckCircle2, FileText, Star, TimerReset } from 'lucide-react'
import { Link } from 'react-router-dom'
import { Loading } from '../components/Loading'
import { MetricCard } from '../components/MetricCard'
import { studentService } from '../services/studentService'
import type { ItemHistorico, ResumoHistorico } from '../types/historico'

export function HistoricoPage() {
  const [resumo, setResumo] = useState<ResumoHistorico | null>(null)
  const [historico, setHistorico] = useState<ItemHistorico[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([studentService.resumo(), studentService.historico()])
      .then(([r, h]) => {
        setResumo(r)
        setHistorico(h)
      })
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <Loading />

  return (
    <div>
      <div className="page-heading">
        <div>
          <h1>Histórico</h1>
          <p>Acompanhe seu desempenho nas entrevistas realizadas.</p>
        </div>
      </div>

      <div className="metric-grid metric-grid--5">
        <MetricCard label="Quantidade total" value={resumo?.quantidade_total ?? 0} icon={<FileText />} />
        <MetricCard label="Quantidade avaliada" value={resumo?.quantidade_avaliada ?? 0} icon={<CheckCircle2 />} />
        <MetricCard label="Média" value={resumo?.media_pontuacoes?.toFixed(2) ?? '-'} icon={<BarChart3 />} />
        <MetricCard label="Melhor pontuação" value={resumo?.melhor_pontuacao?.toFixed(2) ?? '-'} icon={<Star />} />
        <MetricCard label="Última pontuação" value={resumo?.ultima_pontuacao?.toFixed(2) ?? '-'} icon={<TimerReset />} />
      </div>

      <section className="panel">
        <div className="panel__heading">
          <div>
            <h2>Entrevistas realizadas</h2>
            <p>Histórico completo com status e pontuações.</p>
          </div>
        </div>

        <div className="table-wrap">
          <table>
            <thead>
              <tr><th>ID</th><th>Tipo</th><th>Data</th><th>Status</th><th>Pontuação</th><th>Ações</th></tr>
            </thead>
            <tbody>
              {historico.map((item) => (
                <tr key={item.id}>
                  <td>{item.id}</td>
                  <td>Tipo {item.tipo_entrevista_id}</td>
                  <td>{item.data_inicio}</td>
                  <td><span className={`status status--${item.status}`}>{item.status}</span></td>
                  <td>{item.pontuacao_final ?? '-'}</td>
                  <td>{item.status === 'avaliada' && <Link to={`/relatorios/${item.id}`}>Ver relatório</Link>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  )
}
