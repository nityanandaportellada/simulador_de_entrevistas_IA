
import { useEffect, useState } from 'react'
import { BarChart3, MessageSquareText } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { Loading } from '../components/Loading'
import { studentService } from '../services/studentService'
import type { AreaTecnica, SubareaTecnica, TipoEntrevista } from '../types/catalogos'
import type { CriarEntrevistaRequest, PerfilProfissional } from '../types/entrevista'

const PERFIS: { valor: PerfilProfissional; nome: string; basicas: number; intermediarias: number; avancadas: number }[] = [
  { valor: 'estagio_trainee', nome: 'Estágio / Trainee', basicas: 5, intermediarias: 3, avancadas: 0 },
  { valor: 'junior', nome: 'Profissional Júnior', basicas: 3, intermediarias: 4, avancadas: 1 },
  { valor: 'pleno', nome: 'Profissional Pleno', basicas: 1, intermediarias: 4, avancadas: 3 },
  { valor: 'senior', nome: 'Profissional Sênior', basicas: 0, intermediarias: 3, avancadas: 5 }
]

function mensagemErro(erro: unknown): string {
  return erro instanceof Error ? erro.message : 'Ocorreu um erro inesperado. Tente novamente.'
}

export function NovaEntrevistaPage() {
  const navigate = useNavigate()
  const [tipos, setTipos] = useState<TipoEntrevista[]>([])
  const [areas, setAreas] = useState<AreaTecnica[]>([])
  const [subareas, setSubareas] = useState<SubareaTecnica[]>([])
  const [tipoSelecionadoId, setTipoSelecionadoId] = useState<number | null>(null)
  const [perfilSelecionado, setPerfilSelecionado] = useState<PerfilProfissional | ''>('')
  const [areaSelecionadaId, setAreaSelecionadaId] = useState<number | null>(null)
  const [subareaSelecionadaId, setSubareaSelecionadaId] = useState<number | null>(null)
  const [loading, setLoading] = useState(true)
  const [carregandoSubareas, setCarregandoSubareas] = useState(false)
  const [tentativaSubareas, setTentativaSubareas] = useState(0)
  const [criando, setCriando] = useState(false)
  const [erroCarregamento, setErroCarregamento] = useState('')
  const [erroSubareas, setErroSubareas] = useState('')
  const [erroInicio, setErroInicio] = useState('')

  // Carrega somente os tipos e as áreas necessários para configurar a entrevista.
  useEffect(() => {
    let ativo = true
    Promise.all([studentService.listarTipos(), studentService.listarAreas()])
      .then(([tiposRecebidos, areasRecebidas]) => {
        if (!ativo) return
        setTipos(tiposRecebidos.filter((tipo) => tipo.ativo))
        setAreas(areasRecebidas.filter((area) => area.ativo))
      })
      .catch((erro: unknown) => {
        if (ativo) setErroCarregamento(mensagemErro(erro))
      })
      .finally(() => {
        if (ativo) setLoading(false)
      })
    return () => { ativo = false }
  }, [])

  // Identifica o tipo de entrevista e o perfil profissional selecionados.
  const tipoSelecionado = tipos.find((tipo) => tipo.id === tipoSelecionadoId) ?? null
  const perfil = PERFIS.find((item) => item.valor === perfilSelecionado) ?? null
  const precisaArea = Boolean(tipoSelecionado?.usa_area_tecnica)

  // Busca as subáreas somente quando uma área técnica é selecionada.
  useEffect(() => {
    if (!precisaArea || areaSelecionadaId === null) return
    let ativo = true
    setCarregandoSubareas(true)
    setErroSubareas('')
    studentService.listarSubareas(areaSelecionadaId)
      .then((recebidas) => {
        if (ativo) setSubareas(recebidas.filter((subarea) => subarea.ativo && subarea.area_tecnica_id === areaSelecionadaId))
      })
      .catch((erro: unknown) => {
        if (ativo) setErroSubareas(mensagemErro(erro))
      })
      .finally(() => {
        if (ativo) setCarregandoSubareas(false)
      })
    return () => { ativo = false }
  }, [areaSelecionadaId, precisaArea, tentativaSubareas])

  // Quando o tipo muda, limpa a área e a subárea anteriores.
  function selecionarTipo(tipoId: number) {
    if (criando) return
    setTipoSelecionadoId(tipoId)
    setAreaSelecionadaId(null)
    setSubareaSelecionadaId(null)
    setSubareas([])
    setCarregandoSubareas(false)
    setErroSubareas('')
    setErroInicio('')
  }

  // Quando a área muda, limpa a subárea anteriormente selecionada.
  function selecionarArea(valor: string) {
    if (criando) return
    setAreaSelecionadaId(valor ? Number(valor) : null)
    setSubareaSelecionadaId(null)
    setSubareas([])
    setCarregandoSubareas(false)
    setErroSubareas('')
    setErroInicio('')
  }

  // Impede iniciar uma entrevista com dados incompletos.
  const podeIniciar = Boolean(
    tipoSelecionado && perfilSelecionado && !criando && !loading && !carregandoSubareas && !erroSubareas &&
    (!precisaArea || (areaSelecionadaId !== null && subareaSelecionadaId !== null &&
      subareas.some((subarea) => subarea.id === subareaSelecionadaId && subarea.area_tecnica_id === areaSelecionadaId)))
  )

  // Envia o contexto escolhido ao backend e abre a entrevista criada.
  async function iniciar() {
    if (!podeIniciar || !tipoSelecionado || !perfilSelecionado) return
    setErroInicio('')
    setCriando(true)
    try {
      // O backend utiliza o perfil para selecionar exatamente oito perguntas.
      const dados: CriarEntrevistaRequest = {
        tipo_entrevista_id: tipoSelecionado.id,
        perfil_profissional: perfilSelecionado,
        ...(precisaArea ? { area_tecnica_id: areaSelecionadaId, subarea_tecnica_id: subareaSelecionadaId } : {})
      }
      const entrevista = await studentService.criarEntrevista(dados)
      navigate(`/entrevistas/${entrevista.id}`)
    } catch (erro: unknown) {
      setErroInicio(mensagemErro(erro))
    } finally {
      setCriando(false)
    }
  }

  if (loading) return <Loading />

  // Apresenta uma mensagem caso os dados iniciais não possam ser carregados.
  if (erroCarregamento) {
    return (
      <section className="panel">
        <h1>Nova entrevista</h1>
        <p role="alert">Não foi possível carregar os tipos e as áreas: {erroCarregamento}</p>
        <button type="button" className="button" onClick={() => window.location.reload()}>
          Tentar novamente
        </button>
      </section>
    )
  }

  return (
    <div>
      <div className="page-heading">
        <div>
          <h1>Nova entrevista</h1>
          <p>Escolha a modalidade e o perfil profissional. A entrevista terá oito perguntas.</p>
        </div>
      </div>

      <div className="two-column two-column--wide-left">
        <section className="panel">
          <div className="panel__heading">
            <h2>1. Tipo de entrevista</h2>
            <p>Selecione a modalidade que deseja praticar.</p>
          </div>

          {tipos.length === 0 ? (
            <p className="note">Não existem tipos de entrevista ativos no momento.</p>
          ) : (
            <div className="selection-cards">
              {tipos.map((tipo) => (
                <button
                  key={tipo.id}
                  type="button"
                  aria-pressed={tipoSelecionadoId === tipo.id}
                  className={`selection-card ${tipoSelecionadoId === tipo.id ? 'selection-card--active' : ''}`}
                  onClick={() => selecionarTipo(tipo.id)}
                  disabled={criando}
                >
                  <BarChart3 />
                  <strong>{tipo.nome}</strong>
                  <span>
                    {tipo.usa_area_tecnica
                      ? 'Conhecimentos por área e subárea'
                      : 'Competências e experiências profissionais'}
                  </span>
                </button>
              ))}
            </div>
          )}

          <div className="panel__heading" style={{ marginTop: '1.5rem' }}>
            <h2>2. Perfil profissional</h2>
            <p>O perfil define a proporção de questões básicas, intermediárias e avançadas.</p>
          </div>

          <label className="field">
            <span>Perfil para a entrevista</span>
            <select
              value={perfilSelecionado}
              disabled={criando}
              onChange={(evento) => {
                setPerfilSelecionado(evento.target.value as PerfilProfissional | '')
                setErroInicio('')
              }}
            >
              <option value="">Selecione seu perfil</option>
              {PERFIS.map((item) => (
                <option key={item.valor} value={item.valor}>{item.nome}</option>
              ))}
            </select>
          </label>

          {precisaArea && (
            <>
              <div className="panel__heading" style={{ marginTop: '1.5rem' }}>
                <h2>3. Área e subárea técnica</h2>
                <p>Escolha a área profissional e a subárea sobre a qual deseja responder.</p>
              </div>

              <div className="two-column">
                <label className="field">
                  <span>Área técnica</span>
                  <select
                    value={areaSelecionadaId ?? ''}
                    disabled={criando}
                    onChange={(evento) => selecionarArea(evento.target.value)}
                  >
                    <option value="">Selecione uma área</option>
                    {areas.map((area) => (
                      <option key={area.id} value={area.id}>{area.nome}</option>
                    ))}
                  </select>
                </label>

                <label className="field">
                  <span>Subárea técnica</span>
                  <select
                    value={subareaSelecionadaId ?? ''}
                    disabled={criando || areaSelecionadaId === null || carregandoSubareas || Boolean(erroSubareas)}
                    onChange={(evento) => {
                      setSubareaSelecionadaId(evento.target.value ? Number(evento.target.value) : null)
                      setErroInicio('')
                    }}
                  >
                    <option value="">
                      {carregandoSubareas ? 'Carregando subáreas...' : 'Selecione uma subárea'}
                    </option>
                    {subareas.map((subarea) => (
                      <option key={subarea.id} value={subarea.id}>{subarea.nome}</option>
                    ))}
                  </select>
                </label>
              </div>

              {erroSubareas && (
                <div role="alert">
                  <p className="note">Não foi possível carregar as subáreas: {erroSubareas}</p>
                  <button type="button" className="button button--outline" disabled={criando || carregandoSubareas}
                    onClick={() => setTentativaSubareas((anterior) => anterior + 1)}>Tentar carregar novamente</button>
                </div>
              )}

              {!carregandoSubareas && areaSelecionadaId !== null && subareas.length === 0 && !erroSubareas && (
                <p className="note">Esta área não possui subáreas ativas disponíveis.</p>
              )}
            </>
          )}
        </section>

        <section className="panel">
          <div className="panel__heading">
            <h2>Resumo da entrevista</h2>
            <p>Confira sua escolha antes de começar.</p>
          </div>

          {!tipoSelecionado || !perfil ? (
            <div className="empty-state">
              <MessageSquareText size={42} />
              Selecione o tipo de entrevista e o perfil profissional para visualizar o resumo.
            </div>
          ) : (
            <>
              <ol className="question-preview">
                <li><strong>Modalidade:</strong> {tipoSelecionado.nome}</li>
                <li><strong>Perfil:</strong> {perfil.nome}</li>
                <li><strong>Quantidade:</strong> 8 perguntas</li>
                <li><strong>Básicas:</strong> {perfil.basicas}</li>
                <li><strong>Intermediárias:</strong> {perfil.intermediarias}</li>
                <li><strong>Avançadas:</strong> {perfil.avancadas}</li>

                {precisaArea && (
                  <li>
                    <strong>Área:</strong>{' '}
                    {areas.find((area) => area.id === areaSelecionadaId)?.nome ?? 'Não selecionada'}
                  </li>
                )}

                {precisaArea && (
                  <li>
                    <strong>Subárea:</strong>{' '}
                    {subareas.find((subarea) => subarea.id === subareaSelecionadaId)?.nome ?? 'Não selecionada'}
                  </li>
                )}
              </ol>

              <p className="note">
                As perguntas serão escolhidas pelo sistema ao iniciar a entrevista.
                As respostas de referência não são exibidas durante a simulação.
              </p>
            </>
          )}
        </section>
      </div>

      <div className="panel panel--cta">
        <div>
          <h2>Pronto para começar?</h2>
          <p>Após iniciar, responda às oito perguntas e receba sua avaliação ao final.</p>
          {erroInicio && (
            <p className="note" role="alert">
              Não foi possível iniciar a entrevista: {erroInicio}
            </p>
          )}
        </div>

        <button
          type="button"
          className="button button--primary"
          onClick={() => void iniciar()}
          disabled={!podeIniciar}
        >
          {criando ? 'Iniciando...' : 'Iniciar entrevista'}
        </button>
      </div>
    </div>
  )
}
