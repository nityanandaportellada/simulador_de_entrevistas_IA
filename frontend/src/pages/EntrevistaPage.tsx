
import { useEffect, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { Loading } from '../components/Loading'
import { studentService } from '../services/studentService'
import type { Entrevista, EntrevistaPergunta, Resposta } from '../types/entrevista'

const STATUS: Record<Entrevista['status'], string> = {
  em_andamento: 'Em andamento',
  finalizada: 'Finalizada',
  em_analise: 'Em análise',
  avaliada: 'Avaliada',
  erro_analise: 'Erro na análise',
  cancelada: 'Cancelada'
}

function mensagemErro(erro: unknown): string {
  return erro instanceof Error ? erro.message : 'Não foi possível concluir a operação. Tente novamente.'
}

export function EntrevistaPage() {
  const navigate = useNavigate()
  const { id } = useParams()
  const entrevistaId = Number(id)
  const [entrevista, setEntrevista] = useState<Entrevista | null>(null)
  const [perguntas, setPerguntas] = useState<EntrevistaPergunta[]>([])
  const [respostas, setRespostas] = useState<Resposta[]>([])
  const [rascunhos, setRascunhos] = useState<Record<number, string>>({})
  const [indice, setIndice] = useState(0)
  const [loading, setLoading] = useState(true)
  const [salvando, setSalvando] = useState(false)
  const [processando, setProcessando] = useState(false)
  const [erroCarregamento, setErroCarregamento] = useState('')
  const [erroOperacao, setErroOperacao] = useState('')
  const inicioResposta = useRef(Date.now())

  // Recupera a entrevista e as respostas já registradas, sem modificar dados existentes.
  useEffect(() => {
    let ativo = true
    if (!Number.isInteger(entrevistaId) || entrevistaId <= 0) {
      setErroCarregamento('Identificador de entrevista inválido.')
      setLoading(false)
      return
    }
    Promise.all([
      studentService.buscarEntrevista(entrevistaId),
      studentService.listarPerguntasEntrevista(entrevistaId),
      studentService.listarRespostas(entrevistaId)
    ])
      .then(([dados, listaPerguntas, listaRespostas]) => {
        if (!ativo) return
        setEntrevista(dados)
        setPerguntas(listaPerguntas)
        setRespostas(listaRespostas)
        // Ao retornar à entrevista, abre a primeira pergunta ainda sem resposta.
        const pendente = listaPerguntas.findIndex((pergunta) =>
          !listaRespostas.some((resposta) => resposta.pergunta_id === pergunta.pergunta_id)
        )
        setIndice(pendente >= 0 ? pendente : Math.max(0, listaPerguntas.length - 1))
      })
      .catch((erro: unknown) => {
        if (ativo) setErroCarregamento(mensagemErro(erro))
      })
      .finally(() => {
        if (ativo) setLoading(false)
      })
    return () => { ativo = false }
  }, [entrevistaId])

  // Conta o tempo de resposta a partir do momento em que a pergunta é exibida.
  useEffect(() => {
    inicioResposta.current = Date.now()
  }, [indice, entrevistaId, perguntas])

  const respondidas = new Set(respostas.map((resposta) => resposta.pergunta_id))
  const quantidadeRespondida = perguntas.filter((pergunta) => respondidas.has(pergunta.pergunta_id)).length
  const primeiraPendente = perguntas.findIndex((pergunta) => !respondidas.has(pergunta.pergunta_id))
  const limiteNavegacao = primeiraPendente >= 0 ? primeiraPendente : perguntas.length - 1
  const todasRespondidas = perguntas.length > 0 && quantidadeRespondida === perguntas.length
  const atual = perguntas[indice]
  const respostaAtual = respostas.find((resposta) => resposta.pergunta_id === atual?.pergunta_id)
  const texto = atual ? (rascunhos[atual.pergunta_id] ?? respostaAtual?.texto_resposta ?? '') : ''
  const emAndamento = entrevista?.status === 'em_andamento'
  const ocupado = salvando || processando
  const percentual = perguntas.length ? Math.round((quantidadeRespondida / perguntas.length) * 100) : 0

  // Permite consultar respostas anteriores, mas não libera perguntas futuras antecipadamente.
  function irParaPergunta(novoIndice: number) {
    if (ocupado || novoIndice < 0 || novoIndice > limiteNavegacao) return
    setIndice(novoIndice)
    setErroOperacao('')
  }

  // Registra cada resposta uma única vez. Respostas já salvas ficam somente para leitura.
  async function salvarResposta() {
    if (!atual || !emAndamento || respostaAtual || ocupado || !texto.trim()) return
    setSalvando(true)
    setErroOperacao('')
    const conteudo = texto.trim()
    const tempo = Math.max(0, Math.round((Date.now() - inicioResposta.current) / 1000))

    try {
      const resultado = await studentService.responder(entrevistaId, {
        pergunta_id: atual.pergunta_id,
        texto_resposta: conteudo,
        tempo_resposta: tempo
      })
      // A API confirmou a gravação; atualiza a tela sem reenviar a mesma resposta.
      const novaResposta: Resposta = {
        id: resultado.id,
        entrevista_id: resultado.entrevista_id,
        pergunta_id: resultado.pergunta_id,
        texto_resposta: conteudo,
        tempo_resposta: tempo,
        data_resposta: null,
        pergunta_texto_aplicado: atual.pergunta_texto_aplicado,
        exemplo_esperado_aplicado: null,
        competencia_id_aplicada: atual.competencia_id_aplicada,
        competencia_nome_aplicada: atual.competencia_nome_aplicada,
        peso_pergunta_aplicado: atual.peso_pergunta_aplicado,
        usa_star_aplicado: atual.usa_star_aplicado,
        ordem_pergunta_aplicada: atual.ordem_pergunta_aplicada
      }
      setRespostas((anteriores) => [...anteriores, novaResposta])
      setRascunhos((anteriores) => {
        const novos = { ...anteriores }
        delete novos[atual.pergunta_id]
        return novos
      })
      if (indice < perguntas.length - 1) setIndice(indice + 1)
    } catch (erro: unknown) {
      setErroOperacao(`Não foi possível confirmar a resposta: ${mensagemErro(erro)}. Verifique antes de tentar novamente.`)
      // Se houve falha de comunicação, consulta o servidor para não duplicar uma resposta já gravada.
      try {
        const confirmadas = await studentService.listarRespostas(entrevistaId)
        setRespostas(confirmadas)
      } catch { /* Mantém a resposta digitada para recuperação posterior. */ }
    } finally {
      setSalvando(false)
    }
  }

  // Finaliza apenas após todas as respostas; depois solicita a análise existente na API.
  async function finalizarEAnalisar() {
    if (!entrevista || ocupado) return
    const podeAnalisar = entrevista.status === 'finalizada' || entrevista.status === 'erro_analise'
    if (!podeAnalisar && !(emAndamento && todasRespondidas)) return
    setProcessando(true)
    setErroOperacao('')
    try {
      if (entrevista.status === 'em_andamento') {
        await studentService.finalizar(entrevistaId)
        setEntrevista({ ...entrevista, status: 'finalizada' })
      }
      await studentService.analisar(entrevistaId)
      navigate(`/relatorios/${entrevistaId}`)
    } catch (erro: unknown) {
      setErroOperacao(`Não foi possível concluir a finalização ou a análise: ${mensagemErro(erro)}`)
      // A finalização pode ter sido concluída antes de uma falha na análise.
      // Atualiza o estado para permitir tentar a análise novamente, sem finalizar duas vezes.
      try {
        setEntrevista(await studentService.buscarEntrevista(entrevistaId))
      } catch { /* O erro principal permanece visível. */ }
    } finally {
      setProcessando(false)
    }
  }

  async function atualizarSituacao() {
    if (ocupado) return
    setProcessando(true)
    setErroOperacao('')
    try {
      setEntrevista(await studentService.buscarEntrevista(entrevistaId))
    } catch (erro: unknown) {
      setErroOperacao(mensagemErro(erro))
    } finally {
      setProcessando(false)
    }
  }

  if (loading) return <Loading />

  if (erroCarregamento || !entrevista) {
    return (
      <section className="panel">
        <h1>Não foi possível abrir a entrevista</h1>
        <p className="alert alert--error" role="alert">{erroCarregamento || 'Entrevista não encontrada.'}</p>
        <button type="button" className="button button--outline" onClick={() => navigate('/historico')}>
          Voltar ao histórico
        </button>
      </section>
    )
  }

  if (!atual) {
    return <div className="empty-state">Nenhuma pergunta disponível para esta entrevista.</div>
  }

  const nomeTipo = entrevista.tipo_entrevista_nome_aplicado || `Tipo ${entrevista.tipo_entrevista_id}`
  const podeSalvar = emAndamento && !respostaAtual && !ocupado && Boolean(texto.trim())
  const podeFinalizar = emAndamento && todasRespondidas
  const podeReanalisar = entrevista.status === 'finalizada' || entrevista.status === 'erro_analise'

  return (
    <div>
      <div className="page-heading">
        <div>
          <h1>{emAndamento ? 'Entrevista em andamento' : 'Entrevista'}</h1>
          <p>Responda às perguntas em sequência. Cada resposta registrada não poderá ser alterada.</p>
        </div>
      </div>

      <section className="interview-summary" aria-label="Resumo da entrevista">
        <div><span>Modalidade</span><strong>{nomeTipo}</strong></div>
        {entrevista.area_tecnica_nome_aplicado && (
          <div><span>Área</span><strong>{entrevista.area_tecnica_nome_aplicado}</strong></div>
        )}
        {entrevista.subarea_tecnica_nome_aplicado && (
          <div><span>Subárea</span><strong>{entrevista.subarea_tecnica_nome_aplicado}</strong></div>
        )}
        <div><span>Progresso</span><strong>{quantidadeRespondida} de {perguntas.length} respondidas</strong></div>
        <div><span>Status</span><strong>{STATUS[entrevista.status]}</strong></div>
      </section>

      <section className="panel" aria-label="Progresso da entrevista">
        <div className="panel__heading panel__heading--actions">
          <strong>Progresso da entrevista</strong>
          <span>{percentual}% concluído</span>
        </div>
        <div className="progress" role="progressbar" aria-label="Perguntas respondidas" aria-valuemin={0} aria-valuemax={perguntas.length} aria-valuenow={quantidadeRespondida}>
          <div style={{ width: `${percentual}%` }} />
        </div>
      </section>

      <div className="interview-grid">
        <aside className="panel">
          <h2>Etapas da entrevista</h2>
          <p>As próximas perguntas serão liberadas conforme você responder.</p>
          <nav className="step-list" aria-label="Navegação entre perguntas">
            {perguntas.map((pergunta, posicao) => {
              const foiRespondida = respondidas.has(pergunta.pergunta_id)
              const bloqueada = emAndamento && posicao > limiteNavegacao
              return (
                <button
                  key={pergunta.id}
                  type="button"
                  aria-current={posicao === indice ? 'step' : undefined}
                  className={`step-item ${posicao === indice ? 'step-item--active' : ''} ${foiRespondida ? 'step-item--done' : ''}`}
                  onClick={() => irParaPergunta(posicao)}
                  disabled={ocupado || bloqueada}
                >
                  <span>{posicao + 1}</span>
                  <div>
                    <strong>Pergunta {posicao + 1}</strong>
                    <small>{foiRespondida ? 'Respondida' : bloqueada ? 'Aguardando' : posicao === indice ? 'Em resposta' : 'Pendente'}</small>
                  </div>
                </button>
              )
            })}
          </nav>
        </aside>

        <section className="panel">
          <div className="question-card">
            <div className="question-card__eyebrow">
              Pergunta {indice + 1} de {perguntas.length}
              {atual.usa_star_aplicado && <span>Método STAR</span>}
            </div>
            <h2>{atual.pergunta_texto_aplicado}</h2>
          </div>

          {atual.usa_star_aplicado && (
            <p className="note">Sugestão: organize sua resposta com Situação, Tarefa, Ação e Resultado (STAR).</p>
          )}

          <label className="field" htmlFor="texto-resposta">
            <span>Sua resposta</span>
            <textarea
              id="texto-resposta"
              rows={9}
              value={texto}
              onChange={(evento) => {
                setRascunhos((anteriores) => ({ ...anteriores, [atual.pergunta_id]: evento.target.value }))
                if (erroOperacao) setErroOperacao('')
              }}
              placeholder="Descreva sua experiência, suas ações e os resultados..."
              disabled={!emAndamento || Boolean(respostaAtual) || ocupado}
            />
          </label>

          {respostaAtual && <p className="note">Resposta registrada. Ela está disponível para consulta, mas não pode ser modificada.</p>}
          {erroOperacao && <p className="alert alert--error" role="alert">{erroOperacao}</p>}

          <div className="button-row button-row--end">
            <button
              type="button"
              className="button button--outline"
              disabled={ocupado || indice <= 0}
              onClick={() => irParaPergunta(indice - 1)}
            >
              Anterior
            </button>

            {emAndamento && !respostaAtual && (
              <button type="button" className="button button--primary" disabled={!podeSalvar} onClick={() => void salvarResposta()}>
                {salvando ? 'Salvando...' : indice === perguntas.length - 1 ? 'Salvar última resposta' : 'Salvar e continuar'}
              </button>
            )}

            {indice < limiteNavegacao && (
              <button type="button" className="button button--outline" disabled={ocupado} onClick={() => irParaPergunta(indice + 1)}>
                Próxima
              </button>
            )}

            {podeFinalizar && (
              <button type="button" className="button button--primary" disabled={ocupado} onClick={() => void finalizarEAnalisar()}>
                {processando ? 'Finalizando...' : 'Finalizar e solicitar avaliação'}
              </button>
            )}

            {podeReanalisar && (
              <button type="button" className="button button--primary" disabled={ocupado} onClick={() => void finalizarEAnalisar()}>
                {processando ? 'Analisando...' : 'Solicitar avaliação'}
              </button>
            )}

            {entrevista.status === 'em_analise' && (
              <button type="button" className="button button--outline" disabled={ocupado} onClick={() => void atualizarSituacao()}>
                Atualizar situação
              </button>
            )}

            {entrevista.status === 'avaliada' && (
              <button type="button" className="button button--primary" onClick={() => navigate(`/relatorios/${entrevistaId}`)}>
                Ver relatório
              </button>
            )}
          </div>

          {emAndamento && todasRespondidas && <p className="note">Todas as respostas foram registradas. Você já pode finalizar a entrevista.</p>}
          {entrevista.status === 'cancelada' && <p className="note">Esta entrevista foi cancelada e não aceita novas respostas.</p>}
        </section>
      </div>
    </div>
  )
}
