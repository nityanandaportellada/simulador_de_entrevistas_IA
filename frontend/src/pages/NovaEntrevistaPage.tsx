import { useEffect, useMemo, useState } from 'react'
import { BarChart3, MessageSquareText } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { Loading } from '../components/Loading'
import { studentService } from '../services/studentService'
import type { TipoEntrevista } from '../types/catalogos'
import type { Pergunta } from '../types/pergunta'

export function NovaEntrevistaPage() {
  const navigate = useNavigate()
  const [tipos, setTipos] = useState<TipoEntrevista[]>([])
  const [perguntas, setPerguntas] = useState<Pergunta[]>([])
  const [selecionado, setSelecionado] = useState<number | null>(null)
  const [loading, setLoading] = useState(true)
  const [criando, setCriando] = useState(false)

  useEffect(() => {
    Promise.all([studentService.listarTipos(), studentService.listarPerguntas()])
      .then(([t, p]) => {
        setTipos(t.filter((x) => x.ativo))
        setPerguntas(p.filter((x) => x.ativa))
      })
      .finally(() => setLoading(false))
  }, [])

  const perguntasTipo = useMemo(
    () => perguntas.filter((p) => p.tipo_entrevista_id === selecionado),
    [perguntas, selecionado]
  )

  async function iniciar() {
    if (!selecionado) return
    setCriando(true)
    try {
      const entrevista = await studentService.criarEntrevista({
        tipo_entrevista_id: selecionado
      })
      navigate(`/entrevistas/${entrevista.id}`)
    } finally {
      setCriando(false)
    }
  }

  if (loading) return <Loading />

  return (
    <div>
      <div className="page-heading">
        <div>
          <h1>Nova entrevista</h1>
          <p>Escolha o tipo de entrevista e inicie uma simulação com base nos dados disponíveis no sistema.</p>
        </div>
      </div>

      <div className="two-column two-column--wide-left">
        <section className="panel">
          <div className="panel__heading">
            <div>
              <h2>Selecione o tipo de entrevista</h2>
              <p>Cada tipo utiliza suas próprias perguntas cadastradas.</p>
            </div>
          </div>

          <div className="selection-cards">
            {tipos.map((tipo) => (
              <button
                key={tipo.id}
                className={`selection-card ${selecionado === tipo.id ? 'selection-card--active' : ''}`}
                onClick={() => setSelecionado(tipo.id)}
              >
                <BarChart3 />
                <strong>{tipo.nome}</strong>
                <span>{perguntas.filter((p) => p.tipo_entrevista_id === tipo.id).length} perguntas disponíveis</span>
              </button>
            ))}
          </div>
        </section>

        <section className="panel">
          <div className="panel__heading">
            <div>
              <h2>Perguntas disponíveis</h2>
              <p>Conteúdo carregado conforme o tipo selecionado.</p>
            </div>
          </div>

          {!selecionado ? (
            <div className="empty-state">
              <MessageSquareText size={42} />
              Selecione um tipo para visualizar as perguntas.
            </div>
          ) : (
            <ol className="question-preview">
              {perguntasTipo.map((p) => <li key={p.id}>{p.texto}</li>)}
            </ol>
          )}
        </section>
      </div>

      <div className="panel panel--cta">
        <div>
          <h2>Como funciona</h2>
          <p>Escolha o tipo, responda às perguntas, finalize e receba a análise.</p>
        </div>
        <button className="button button--primary" onClick={iniciar} disabled={!selecionado || criando}>
          {criando ? 'Iniciando...' : 'Iniciar entrevista'}
        </button>
      </div>
    </div>
  )
}
