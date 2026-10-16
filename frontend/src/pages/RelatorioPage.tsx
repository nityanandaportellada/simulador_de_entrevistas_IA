import { useEffect, useState } from 'react'
import { CheckCircle2, MessageSquareText, Trophy } from 'lucide-react'
import { useParams } from 'react-router-dom'
import { Loading } from '../components/Loading'
import { MetricCard } from '../components/MetricCard'
import { studentService } from '../services/studentService'
import type { RelatorioEntrevista } from '../types/relatorio'

export function RelatorioPage() {
  const { id } = useParams()
  const [relatorio, setRelatorio] = useState<RelatorioEntrevista | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    studentService.relatorio(Number(id))
      .then(setRelatorio)
      .finally(() => setLoading(false))
  }, [id])

  if (loading || !relatorio) return <Loading />

  return (
    <div>
      <div className="page-heading">
        <div>
          <h1>Relatório da entrevista</h1>
          <p>Confira seu desempenho, feedbacks e pontos de desenvolvimento.</p>
        </div>
      </div>

      <div className="metric-grid metric-grid--4">
        <MetricCard label="Pontuação final" value={relatorio.entrevista.pontuacao_final?.toFixed(2) ?? '-'} icon={<Trophy />} />
        <MetricCard label="Classificação" value={relatorio.classificacao} icon={<CheckCircle2 />} />
        <MetricCard label="Quantidade de respostas" value={relatorio.quantidade_respostas} icon={<MessageSquareText />} />
        <MetricCard label="Quantidade de avaliações" value={relatorio.quantidade_avaliacoes} icon={<CheckCircle2 />} />
      </div>

      <section className="panel">
        <div className="panel__heading"><div><h2>Desempenho por critérios</h2><p>Escala de 0 a 10.</p></div></div>
        <div className="progress-list">
          {relatorio.desempenho_criterios.map((item) => (
            <div className="progress-row" key={item.criterio_id}>
              <span>{item.criterio}</span>
              <div className="progress"><div style={{ width: `${item.media * 10}%` }} /></div>
              <strong>{item.media.toFixed(1)}</strong>
            </div>
          ))}
        </div>

        <div className="highlight-grid">
          <div className="highlight highlight--good">
            <strong>Melhor critério</strong>
            <span>{relatorio.destaques.melhor_criterio?.criterio ?? '-'}</span>
          </div>
          <div className="highlight highlight--warn">
            <strong>Critério a desenvolver</strong>
            <span>{relatorio.destaques.criterio_a_desenvolver?.criterio ?? '-'}</span>
          </div>
        </div>
      </section>

      <section className="panel">
        <div className="panel__heading"><div><h2>Suas respostas na entrevista</h2><p>Revise respostas, feedbacks e notas.</p></div></div>
        <div className="accordion-list">
          {relatorio.respostas.map((item, index) => (
            <details key={item.resposta_id} open={index === 0}>
              <summary>
                <span>{index + 1}. {item.pergunta}</span>
                <strong>{item.avaliacao?.pontuacao?.toFixed(1) ?? '-'}</strong>
              </summary>
              <div className="response-detail">
                <div>
                  <h3>Sua resposta</h3>
                  <p>{item.texto_resposta}</p>
                </div>
                <div>
                  <h3>Feedback geral</h3>
                  <p>{item.avaliacao?.feedback ?? 'Sem feedback.'}</p>
                </div>
                <div>
                  <h3>Pontos fortes</h3>
                  <ul>{item.avaliacao?.pontos_fortes.map((x) => <li key={x}>{x}</li>)}</ul>
                </div>
                <div>
                  <h3>Pontos de melhoria</h3>
                  <ul>{item.avaliacao?.pontos_melhoria.map((x) => <li key={x}>{x}</li>)}</ul>
                </div>
              </div>
            </details>
          ))}
        </div>
      </section>
    </div>
  )
}
