
import { useEffect, useState } from 'react'
import { CheckCircle2, FileText, MessageSquareText, Trophy } from 'lucide-react'
import { Link, useParams } from 'react-router-dom'
import { Loading } from '../components/Loading'
import { MetricCard } from '../components/MetricCard'
import { ApiError } from '../services/api'
import { studentService } from '../services/studentService'
import type { RelatorioEntrevista } from '../types/relatorio'

// Formata as notas na mesma escala usada pelo backend.
function nota(valor: number | null | undefined, casas = 1): string {
  return valor === null || valor === undefined || !Number.isFinite(valor) ? '-' : valor.toFixed(casas)
}

function percentual(valor: number): number {
  return Number.isFinite(valor) ? Math.min(100, Math.max(0, valor * 10)) : 0
}

function dataBrasileira(valor: string | null): string {
  if (!valor) return '-'
  // O banco grava horários locais sem fuso; não os converta automaticamente para UTC.
  const iso = valor.includes('T') ? valor : valor.replace(' ', 'T')
  const data = new Date(iso)
  return Number.isNaN(data.getTime()) ? valor : data.toLocaleString('pt-BR')
}

function mensagemErro(erro: unknown): string {
  if (erro instanceof ApiError && erro.status === 409) {
    // O backend usa 409 tanto para avaliação pendente como para histórico inconsistente.
    return typeof erro.detail === 'string' && erro.detail.trim()
      ? erro.detail
      : 'O relatório ainda não está disponível ou possui inconsistências. Confira a situação da entrevista.'
  }
  return erro instanceof Error ? erro.message : 'Não foi possível carregar o relatório.'
}

export function RelatorioPage() {
  const { id } = useParams()
  const entrevistaId = Number(id)
  const [relatorio, setRelatorio] = useState<RelatorioEntrevista | null>(null)
  const [loading, setLoading] = useState(true)
  const [erro, setErro] = useState('')
  const [tentativas, setTentativas] = useState(0)

  // A API só libera o relatório depois da avaliação e da verificação de acesso.
  useEffect(() => {
    let ativo = true
    setLoading(true)
    setErro('')
    setRelatorio(null)
    if (!Number.isInteger(entrevistaId) || entrevistaId <= 0) {
      setErro('Identificador de entrevista inválido.')
      setLoading(false)
      return () => { ativo = false }
    }
    studentService.relatorio(entrevistaId)
      .then((dados) => { if (ativo) setRelatorio(dados) })
      .catch((falha: unknown) => { if (ativo) setErro(mensagemErro(falha)) })
      .finally(() => { if (ativo) setLoading(false) })
    return () => { ativo = false }
  }, [entrevistaId, tentativas])

  if (loading) return <Loading />

  // Evita apresentar um relatório parcial mesmo se uma resposta inválida chegar ao cliente.
  const relatorioCompleto = relatorio !== null && relatorio.entrevista.status === 'avaliada' &&
    relatorio.entrevista.pontuacao_final !== null && Number.isFinite(relatorio.entrevista.pontuacao_final) &&
    relatorio.quantidade_respostas > 0 && relatorio.quantidade_avaliacoes === relatorio.quantidade_respostas &&
    relatorio.respostas.length === relatorio.quantidade_respostas &&
    relatorio.respostas.every((resposta) => resposta.avaliacao !== null)

  if (erro || !relatorioCompleto || !relatorio) {
    return (
      <section className="panel">
        <h1>Relatório indisponível</h1>
        <p className="alert alert--error" role="alert">
          {erro || 'O relatório ainda não está completo ou apresenta inconsistências. Confira a situação da entrevista.'}
        </p>
        <div className="button-row">
          <button type="button" className="button button--primary" onClick={() => setTentativas((valor) => valor + 1)}>
            Tentar novamente
          </button>
          {Number.isInteger(entrevistaId) && entrevistaId > 0 && (
            <Link className="button button--outline" to={`/entrevistas/${entrevistaId}`}>Ver entrevista</Link>
          )}
          <Link className="button button--outline" to="/relatorios">Voltar aos relatórios</Link>
        </div>
      </section>
    )
  }

  const entrevista = relatorio.entrevista
  const contextoTecnico = entrevista.area_tecnica
    ? `${entrevista.area_tecnica}${entrevista.subarea_tecnica ? ` / ${entrevista.subarea_tecnica}` : ''}`
    : null
  const criterioMelhor = relatorio.destaques?.melhor_criterio
  const criterioMelhoria = relatorio.destaques?.criterio_a_desenvolver
  const totalAvaliadas = relatorio.respostas.filter((resposta) => resposta.avaliacao !== null).length
  const criteriosOrdenados = [...relatorio.desempenho_criterios].sort((a, b) =>
    (a.ordem_criterio ?? 9999) - (b.ordem_criterio ?? 9999)
  )

  return (
    <div>
      <div className="page-heading">
        <div>
          <h1>Relatório da entrevista #{entrevista.id}</h1>
          <p>Consulte sua avaliação, os critérios utilizados e as recomendações para evoluir.</p>
        </div>
        <Link className="button button--outline" to="/relatorios">Voltar aos relatórios</Link>
      </div>

      <section className="interview-summary" aria-label="Dados da entrevista">
        <div><span>Modalidade</span><strong>{entrevista.tipo_entrevista ?? `Tipo ${entrevista.tipo_entrevista_id}`}</strong></div>
        {contextoTecnico && <div><span>Área / subárea</span><strong>{contextoTecnico}</strong></div>}
        <div><span>Início</span><strong>{dataBrasileira(entrevista.data_inicio)}</strong></div>
        <div><span>Conclusão</span><strong>{dataBrasileira(entrevista.data_fim)}</strong></div>
        <div><span>Status</span><strong>Avaliada</strong></div>
      </section>

      <div className="metric-grid metric-grid--4">
        <MetricCard label="Pontuação final (0 a 10)" value={nota(entrevista.pontuacao_final, 2)} icon={<Trophy />} />
        <MetricCard label="Classificação" value={relatorio.classificacao ?? '-'} icon={<CheckCircle2 />} />
        <MetricCard label="Respostas avaliadas" value={`${totalAvaliadas} de ${relatorio.quantidade_respostas}`} icon={<MessageSquareText />} />
        <MetricCard label="Critérios avaliados" value={criteriosOrdenados.length} icon={<FileText />} />
      </div>

      <section className="panel">
        <div className="panel__heading">
          <h2>Desempenho por critério</h2>
          <p>Notas médias por critério na escala de 0 a 10. Os pesos são os registrados no momento da avaliação.</p>
        </div>
        {criteriosOrdenados.length ? (
          <div className="progress-list">
            {criteriosOrdenados.map((item) => (
              <div key={item.criterio_id}>
                <div className="progress-row">
                  <span title={item.criterio_descricao ?? undefined}>{item.criterio}</span>
                  <div className="progress" role="progressbar" aria-label={item.criterio} aria-valuemin={0} aria-valuemax={10} aria-valuenow={item.media}>
                    <div style={{ width: `${percentual(item.media)}%` }} />
                  </div>
                  <strong>{nota(item.media)}</strong>
                </div>
                <small>Peso: {nota(item.peso, 2)} · {item.quantidade_avaliacoes} avaliação(ões)</small>
              </div>
            ))}
          </div>
        ) : <p className="empty-state">Não há notas por critério disponíveis.</p>}

        <div className="highlight-grid">
          <div className="highlight highlight--good">
            <strong>Critério de maior destaque</strong>
            <span>{criterioMelhor ? `${criterioMelhor.criterio} — ${nota(criterioMelhor.media)}/10` : 'Não identificado'}</span>
          </div>
          <div className="highlight highlight--warn">
            <strong>Critério para desenvolver</strong>
            <span>{criterioMelhoria ? `${criterioMelhoria.criterio} — ${nota(criterioMelhoria.media)}/10` : 'Não identificado'}</span>
          </div>
        </div>
      </section>

      {entrevista.observacoes && (
        <section className="panel">
          <h2>Observações da entrevista</h2>
          <p style={{ whiteSpace: 'pre-wrap', overflowWrap: 'anywhere' }}>{entrevista.observacoes}</p>
        </section>
      )}

      <section className="panel">
        <div className="panel__heading">
          <h2>Avaliação de cada resposta</h2>
          <p>Consulte suas respostas, feedbacks, pontos fortes, oportunidades de melhoria e notas por critério.</p>
        </div>
        {relatorio.respostas.length === 0 ? (
          <p className="empty-state">Nenhuma resposta foi encontrada para esta entrevista.</p>
        ) : (
          <div className="accordion-list">
            {relatorio.respostas.map((item, indice) => {
              const avaliacao = item.avaliacao
              const notasOrdenadas = [...(avaliacao?.criterios ?? [])].sort((a, b) =>
                (a.ordem_criterio ?? 9999) - (b.ordem_criterio ?? 9999)
              )
              return (
                <details key={item.resposta_id} open={indice === 0}>
                  <summary>
                    <span>{indice + 1}. {item.pergunta}</span>
                    <strong>{nota(avaliacao?.pontuacao)}/10</strong>
                  </summary>
                  <div className="response-detail">
                    <div>
                      <h3>Contexto da pergunta</h3>
                      {item.competencia && <p><strong>Competência:</strong> {item.competencia}</p>}
                      {item.area_tecnica && (
                        <p><strong>Área:</strong> {item.area_tecnica}{item.subarea_tecnica ? ` / ${item.subarea_tecnica}` : ''}</p>
                      )}
                      <p><strong>Orientação STAR:</strong> {item.usa_star ? 'Aplicável' : 'Não aplicável'}</p>
                      {item.tempo_resposta !== null && <p><strong>Tempo informado:</strong> {item.tempo_resposta} segundo(s)</p>}
                    </div>
                    <div>
                      <h3>Sua resposta</h3>
                      <p style={{ whiteSpace: 'pre-wrap', overflowWrap: 'anywhere' }}>{item.texto_resposta}</p>
                    </div>
                    <div>
                      <h3>Feedback da avaliação</h3>
                      <p style={{ whiteSpace: 'pre-wrap', overflowWrap: 'anywhere' }}>{avaliacao?.feedback || 'Sem feedback registrado.'}</p>
                    </div>
                    <div>
                      <h3>Pontos fortes</h3>
                      {avaliacao?.pontos_fortes?.length ? (
                        <ul>{avaliacao.pontos_fortes.map((ponto, i) => <li key={i}>{ponto}</li>)}</ul>
                      ) : <p>Nenhum ponto forte registrado.</p>}
                    </div>
                    <div>
                      <h3>Oportunidades de melhoria</h3>
                      {avaliacao?.pontos_melhoria?.length ? (
                        <ul>{avaliacao.pontos_melhoria.map((ponto, i) => <li key={i}>{ponto}</li>)}</ul>
                      ) : <p>Nenhuma oportunidade de melhoria registrada.</p>}
                    </div>
                    <div>
                      <h3>Notas por critério</h3>
                      {notasOrdenadas.length ? (
                        <ul>
                          {notasOrdenadas.map((criterio) => (
                            <li key={criterio.criterio_id}>
                              <strong>{criterio.criterio}: {nota(criterio.nota)}/10</strong>
                              <span> (peso {nota(criterio.peso_criterio, 2)})</span>
                              {criterio.observacao && <p>{criterio.observacao}</p>}
                            </li>
                          ))}
                        </ul>
                      ) : <p>Sem notas detalhadas registradas.</p>}
                    </div>
                    {item.exemplo_esperado && (
                      <div>
                        <h3>Resposta de referência</h3>
                        <p className="note">Exemplo utilizado como orientação pela avaliação. Outras respostas corretas também são possíveis.</p>
                        <p style={{ whiteSpace: 'pre-wrap', overflowWrap: 'anywhere' }}>{item.exemplo_esperado}</p>
                      </div>
                    )}
                  </div>
                </details>
              )
            })}
          </div>
        )}
      </section>
    </div>
  )
}
