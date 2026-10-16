import { useEffect, useMemo, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { Loading } from '../components/Loading'
import { studentService } from '../services/studentService'
import type { Entrevista, Resposta } from '../types/entrevista'
import type { Pergunta } from '../types/pergunta'

export function EntrevistaPage() {
  const navigate = useNavigate()
  const { id } = useParams()
  const entrevistaId = Number(id)

  const [entrevista, setEntrevista] = useState<Entrevista | null>(null)
  const [perguntas, setPerguntas] = useState<Pergunta[]>([])
  const [respostas, setRespostas] = useState<Resposta[]>([])
  const [indice, setIndice] = useState(0)
  const [texto, setTexto] = useState('')
  const [salvando, setSalvando] = useState(false)
  const [loading, setLoading] = useState(true)
  const [inicioResposta, setInicioResposta] = useState(Date.now())

  useEffect(() => {
    Promise.all([
      studentService.buscarEntrevista(entrevistaId),
      studentService.listarPerguntas(),
      studentService.listarRespostas(entrevistaId)
    ])
      .then(([e, p, r]) => {
        setEntrevista(e)
        setPerguntas(
          p
            .filter((x) => x.ativa && x.tipo_entrevista_id === e.tipo_entrevista_id)
            .sort((a, b) => (a.ordem ?? 9999) - (b.ordem ?? 9999))
        )
        setRespostas(r)
      })
      .finally(() => setLoading(false))
  }, [entrevistaId])

  const atual = perguntas[indice]
  const respondida = useMemo(
    () => respostas.find((r) => r.pergunta_id === atual?.id),
    [respostas, atual]
  )

  useEffect(() => {
    setTexto(respondida?.texto_resposta ?? '')
    setInicioResposta(Date.now())
  }, [respondida, indice])

  async function salvar() {
    if (!atual || !texto.trim() || respondida) return

    setSalvando(true)
    try {
      await studentService.responder(entrevistaId, {
        pergunta_id: atual.id,
        texto_resposta: texto.trim(),
        tempo_resposta: Math.max(0, Math.round((Date.now() - inicioResposta) / 1000))
      })
      const novas = await studentService.listarRespostas(entrevistaId)
      setRespostas(novas)
      if (indice < perguntas.length - 1) setIndice((v) => v + 1)
    } finally {
      setSalvando(false)
    }
  }

  async function finalizar() {
    await studentService.finalizar(entrevistaId)
    await studentService.analisar(entrevistaId)
    navigate(`/relatorios/${entrevistaId}`)
  }

  if (loading || !entrevista) return <Loading />
  if (!atual) return <div className="empty-state">Nenhuma pergunta disponível para esta entrevista.</div>

  const podeFinalizar = respostas.length === perguntas.length

  return (
    <div>
      <div className="page-heading">
        <div>
          <h1>Entrevista em andamento</h1>
          <p>Responda às perguntas por escrito e finalize quando concluir todas.</p>
        </div>
      </div>

      <section className="interview-summary">
        <div><span>Tipo</span><strong>#{entrevista.tipo_entrevista_id}</strong></div>
        <div><span>Pergunta</span><strong>{indice + 1} de {perguntas.length}</strong></div>
        <div><span>Status</span><strong>{entrevista.status}</strong></div>
      </section>

      <div className="interview-grid">
        <aside className="panel">
          <h2>Perguntas da entrevista</h2>
          <div className="step-list">
            {perguntas.map((p, i) => {
              const done = respostas.some((r) => r.pergunta_id === p.id)
              return (
                <button
                  key={p.id}
                  onClick={() => setIndice(i)}
                  className={`step-item ${i === indice ? 'step-item--active' : ''} ${done ? 'step-item--done' : ''}`}
                >
                  <span>{i + 1}</span>
                  <div>
                    <strong>{done ? 'Respondida' : 'Pergunta'}</strong>
                    <small>{p.texto}</small>
                  </div>
                </button>
              )
            })}
          </div>
        </aside>

        <section className="panel">
          <div className="question-card">
            <div className="question-card__eyebrow">
              Pergunta atual
              {atual.usa_star && <span>Método STAR recomendado</span>}
            </div>
            <h2>{atual.texto}</h2>
          </div>

          <label className="field">
            <span>Sua resposta</span>
            <textarea
              rows={10}
              value={texto}
              onChange={(e) => setTexto(e.target.value)}
              placeholder="Digite sua resposta aqui..."
              disabled={Boolean(respondida)}
            />
          </label>

          <div className="button-row button-row--end">
            {!respondida && (
              <button className="button button--outline" onClick={salvar} disabled={!texto.trim() || salvando}>
                {salvando ? 'Salvando...' : 'Salvar resposta'}
              </button>
            )}

            <button className="button button--primary" disabled={!podeFinalizar} onClick={finalizar}>
              Finalizar entrevista
            </button>
          </div>
        </section>
      </div>
    </div>
  )
}
