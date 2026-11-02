
import { useEffect, useMemo, useState } from 'react'
import { BarChart3, CheckCircle2, FileText, Star, TimerReset } from 'lucide-react'
import { Link } from 'react-router-dom'
import { Loading } from '../components/Loading'
import { MetricCard } from '../components/MetricCard'
import { studentService } from '../services/studentService'
import type { EvolucaoCriterios, ItemHistorico, ResumoHistorico } from '../types/historico'

type Coluna = 'id' | 'modalidade' | 'area' | 'data' | 'situacao' | 'nota' | 'acao'
const COLUNAS: { campo: Coluna; titulo: string }[] = [
  { campo: 'id', titulo: 'Entrevista' }, { campo: 'modalidade', titulo: 'Modalidade' },
  { campo: 'area', titulo: 'Área / subárea' }, { campo: 'data', titulo: 'Data' },
  { campo: 'situacao', titulo: 'Situação' }, { campo: 'nota', titulo: 'Nota' },
  { campo: 'acao', titulo: 'Ação' }
]
const compararTexto = new Intl.Collator('pt-BR', { sensitivity: 'base', numeric: true })
const SITUACOES: Record<ItemHistorico['status'], string> = {
  em_andamento: 'Em andamento', finalizada: 'Finalizada', em_analise: 'Em análise',
  avaliada: 'Avaliada', erro_analise: 'Erro na análise', cancelada: 'Cancelada'
}

function formatarData(valor: string): string {
  const data = new Date(valor.includes('T') ? valor : valor.replace(' ', 'T'))
  return Number.isNaN(data.getTime()) ? valor : data.toLocaleString('pt-BR')
}

function formatarNota(valor: number | null | undefined): string {
  return valor === null || valor === undefined ? '-' : valor.toFixed(2)
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
  const [tentativa, setTentativa] = useState(0)
  const [tipoFiltro, setTipoFiltro] = useState('todos')
  const [statusFiltro, setStatusFiltro] = useState('todos')
  const [busca, setBusca] = useState('')
  const [primeiroId, setPrimeiroId] = useState('')
  const [segundoId, setSegundoId] = useState('')
  const [ordenacao, setOrdenacao] = useState<{ campo: Coluna; direcao: 'asc' | 'desc' }>({ campo: 'data', direcao: 'desc' })
  const [ordenacaoCriterios, setOrdenacaoCriterios] = useState<{ campo: 'nome' | 'antes' | 'depois' | 'diferenca'; direcao: 'asc' | 'desc' }>({ campo: 'nome', direcao: 'asc' })

  // Consulta apenas dados do usuário autenticado, já filtrados no backend.
  useEffect(() => {
    let ativo = true
    setLoading(true)
    setErro('')
    Promise.all([studentService.resumo(), studentService.historico(), studentService.evolucaoCriterios()])
      .then(([dadosResumo, dadosHistorico, dadosCriterios]) => {
        if (!ativo) return
        setResumo(dadosResumo)
        setHistorico(dadosHistorico)
        setEvolucaoCriterios(dadosCriterios)
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

  // Ordena apenas os resultados filtrados; notas ausentes permanecem ao final.
  const filtradas = useMemo(() => {
    function valor(item: ItemHistorico): string | number | null {
      if (ordenacao.campo === 'id') return item.id
      if (ordenacao.campo === 'modalidade') return item.tipo_entrevista ?? `Tipo ${item.tipo_entrevista_id}`
      if (ordenacao.campo === 'area') return item.area_tecnica ? `${item.area_tecnica} / ${item.subarea_tecnica ?? ''}` : null
      if (ordenacao.campo === 'data') return item.data_inicio
      if (ordenacao.campo === 'situacao') return SITUACOES[item.status]
      if (ordenacao.campo === 'nota') return item.status === 'avaliada' && item.pontuacao_final !== null && Number.isFinite(item.pontuacao_final) ? item.pontuacao_final : null
      return item.status === 'avaliada' ? 'Ver relatório' : item.status === 'cancelada' ? null : item.status === 'em_andamento' ? 'Continuar' : 'Ver situação'
    }
    const termo = busca.trim().toLocaleLowerCase('pt-BR')
    return historico.filter((item) => {
      if (tipoFiltro !== 'todos' && item.tipo_entrevista_id !== Number(tipoFiltro)) return false
      if (statusFiltro !== 'todos' && item.status !== statusFiltro) return false
      const conteudo = `${item.id} ${item.tipo_entrevista ?? ''} ${item.area_tecnica ?? ''} ${item.subarea_tecnica ?? ''}`.toLocaleLowerCase('pt-BR')
      return !termo || conteudo.includes(termo)
    }).sort((a, b) => {
      const x = valor(a), y = valor(b)
      if (x === null && y === null) return b.id - a.id
      if (x === null) return 1
      if (y === null) return -1
      const comparacao = typeof x === 'number' && typeof y === 'number' ? x - y : compararTexto.compare(String(x), String(y))
      return comparacao ? comparacao * (ordenacao.direcao === 'asc' ? 1 : -1) : b.id - a.id
    })
  }, [historico, tipoFiltro, statusFiltro, busca, ordenacao])

  function ordenar(campo: Coluna) {
    setOrdenacao((atual) => ({ campo, direcao: atual.campo === campo && atual.direcao === 'asc' ? 'desc' : 'asc' }))
  }

  const avaliadas = useMemo(() => historico.filter((item) => item.status === 'avaliada' && item.pontuacao_final !== null), [historico])
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
  }).sort((a, b) => {
    function valor(item: typeof a) {
      if (ordenacaoCriterios.campo === 'nome') return item.nome
      if (ordenacaoCriterios.campo === 'antes') return item.antes
      if (ordenacaoCriterios.campo === 'depois') return item.depois
      return item.depois - item.antes
    }
    const x = valor(a), y = valor(b)
    const comparacao = typeof x === 'number' && typeof y === 'number' ? x - y : compararTexto.compare(String(x), String(y))
    return comparacao ? comparacao * (ordenacaoCriterios.direcao === 'asc' ? 1 : -1) : a.id - b.id
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
          As médias gerais acima consideram todo o histórico avaliado. Clique nos cabeçalhos para ordenar.
        </p>

        {filtradas.length === 0 ? (
          <div className="empty-state">Nenhuma entrevista corresponde aos filtros selecionados.</div>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  {COLUNAS.map(({ campo, titulo }) => {
                    const ativo = ordenacao.campo === campo
                    return <th key={campo} scope="col" aria-sort={ativo ? ordenacao.direcao === 'asc' ? 'ascending' : 'descending' : 'none'}>
                      <button type="button" onClick={() => ordenar(campo)} aria-label={`Ordenar por ${titulo}`}
                        style={{ border: 0, background: 'transparent', padding: 0, color: 'inherit', font: 'inherit', fontWeight: 'inherit', cursor: 'pointer', whiteSpace: 'nowrap' }}>
                        {titulo} {ativo ? ordenacao.direcao === 'asc' ? '↑' : '↓' : '↕'}
                      </button>
                    </th>
                  })}
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

            {criteriosComparados.length > 0 && (
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      {([['nome', 'Critério comum'], ['antes', 'Primeira'], ['depois', 'Segunda'], ['diferenca', 'Diferença']] as const).map(([campo, titulo]) => {
                        const ativo = ordenacaoCriterios.campo === campo
                        return <th key={campo} scope="col" aria-sort={ativo ? ordenacaoCriterios.direcao === 'asc' ? 'ascending' : 'descending' : 'none'}>
                          <button type="button" aria-label={`Ordenar por ${titulo}`}
                            onClick={() => setOrdenacaoCriterios((atual) => ({ campo, direcao: atual.campo === campo && atual.direcao === 'asc' ? 'desc' : 'asc' }))}
                            style={{ border: 0, background: 'transparent', padding: 0, color: 'inherit', font: 'inherit', fontWeight: 'inherit', cursor: 'pointer' }}>
                            {titulo} {ativo ? ordenacaoCriterios.direcao === 'asc' ? '↑' : '↓' : '↕'}
                          </button>
                        </th>
                      })}
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
