
import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { Loading } from '../components/Loading'
import { studentService } from '../services/studentService'
import type { ItemHistorico } from '../types/historico'

type Coluna = 'id' | 'modalidade' | 'area' | 'data' | 'nota' | 'acao'
const COLUNAS: { campo: Coluna; titulo: string }[] = [
  { campo: 'id', titulo: 'Entrevista' }, { campo: 'modalidade', titulo: 'Modalidade' },
  { campo: 'area', titulo: 'Área / subárea' }, { campo: 'data', titulo: 'Data' },
  { campo: 'nota', titulo: 'Pontuação' }, { campo: 'acao', titulo: 'Ação' }
]
const compararTexto = new Intl.Collator('pt-BR', { sensitivity: 'base', numeric: true })
function dataFormatada(valor: string): string {
  const data = new Date(valor.includes('T') ? valor : valor.replace(' ', 'T'))
  return Number.isNaN(data.getTime()) ? valor : data.toLocaleDateString('pt-BR')
}

export function RelatoriosPage() {
  const [entrevistas, setEntrevistas] = useState<ItemHistorico[]>([])
  const [loading, setLoading] = useState(true)
  const [erro, setErro] = useState('')
  const [tentativa, setTentativa] = useState(0)
  const [tipoFiltro, setTipoFiltro] = useState('todos')
  const [pesquisa, setPesquisa] = useState('')
  const [ordenacao, setOrdenacao] = useState<{ campo: Coluna; direcao: 'asc' | 'desc' }>({ campo: 'data', direcao: 'desc' })

  useEffect(() => {
    let ativo = true
    setLoading(true)
    setErro('')

    studentService.historico()
      .then((dados) => {
        if (ativo) setEntrevistas(dados.filter((item) => item.status === 'avaliada' && item.pontuacao_final !== null && Number.isFinite(item.pontuacao_final) && item.pontuacao_final >= 0 && item.pontuacao_final <= 10))
      })
      .catch((falha: unknown) => {
        if (ativo) setErro(falha instanceof Error ? falha.message : 'Erro ao carregar relatórios.')
      })
      .finally(() => { if (ativo) setLoading(false) })

    return () => { ativo = false }
  }, [tentativa])

  const tipos = useMemo(() => {
    const unicos = new Map<number, string>()
    entrevistas.forEach((item) => {
      unicos.set(item.tipo_entrevista_id, item.tipo_entrevista ?? `Tipo ${item.tipo_entrevista_id}`)
    })
    return [...unicos].sort((a, b) => a[1].localeCompare(b[1], 'pt-BR'))
  }, [entrevistas])

  const filtradas = useMemo(() => {
    const termo = pesquisa.trim().toLocaleLowerCase('pt-BR')

    function valor(item: ItemHistorico): string | number | null {
      if (ordenacao.campo === 'id') return item.id
      if (ordenacao.campo === 'modalidade') return item.tipo_entrevista ?? `Tipo ${item.tipo_entrevista_id}`
      if (ordenacao.campo === 'area') return item.area_tecnica ? `${item.area_tecnica} / ${item.subarea_tecnica ?? ''}` : null
      if (ordenacao.campo === 'data') return item.data_fim ?? item.data_inicio
      if (ordenacao.campo === 'nota') return item.pontuacao_final !== null && Number.isFinite(item.pontuacao_final) ? item.pontuacao_final : null
      return 'Abrir relatório'
    }
    return entrevistas.filter((item) => {
      if (tipoFiltro !== 'todos' && item.tipo_entrevista_id !== Number(tipoFiltro)) return false
      const conteudo = `${item.id} ${item.tipo_entrevista ?? ''} ${item.area_tecnica ?? ''} ${item.subarea_tecnica ?? ''}`.toLocaleLowerCase('pt-BR')
      return !termo || conteudo.includes(termo)
    }).sort((a, b) => {
      const x = valor(a), y = valor(b)
      if (x === null && y === null) return b.id - a.id
      if (x === null) return 1
      if (y === null) return -1
      const resultado = typeof x === 'number' && typeof y === 'number' ? x - y : compararTexto.compare(String(x), String(y))
      return resultado ? resultado * (ordenacao.direcao === 'asc' ? 1 : -1) : b.id - a.id
    })
  }, [entrevistas, tipoFiltro, pesquisa, ordenacao])

  function ordenar(campo: Coluna) {
    setOrdenacao((atual) => ({ campo, direcao: atual.campo === campo && atual.direcao === 'asc' ? 'desc' : 'asc' }))
  }

  if (loading) return <Loading />

  if (erro) return (
    <section className="panel">
      <h1>Relatórios indisponíveis</h1>
      <p className="alert alert--error" role="alert">{erro}</p>
      <button
        type="button"
        className="button button--primary"
        onClick={() => setTentativa((valor) => valor + 1)}
      >
        Tentar novamente
      </button>
    </section>
  )

  return (
    <div>
      <div className="page-heading">
        <div>
          <h1>Relatórios</h1>
          <p>Acesse os resultados das entrevistas avaliadas pela IA.</p>
        </div>
        <Link className="button button--outline" to="/historico">Ver histórico completo</Link>
      </div>

      <section className="panel">
        <div className="panel__heading">
          <h2>Consultar relatórios</h2>
          <p>{entrevistas.length} entrevista(s) avaliada(s) disponível(is).</p>
        </div>

        <div className="two-column" style={{ marginBottom: '1rem' }}>
          <label className="field">
            Modalidade
            <select value={tipoFiltro} onChange={(evento) => setTipoFiltro(evento.target.value)}>
              <option value="todos">Todas as modalidades</option>
              {tipos.map(([id, nome]) => (
                <option value={id} key={id}>{nome}</option>
              ))}
            </select>
          </label>

          <label className="field">
            Ordenar por
            <select value={ordenacao.campo === 'data' ? ordenacao.direcao === 'desc' ? 'recentes' : 'antigos' : ordenacao.campo === 'nota' ? ordenacao.direcao === 'desc' ? 'maior_nota' : 'menor_nota' : 'coluna'}
              onChange={(evento) => {
                const valor = evento.target.value
                setOrdenacao({ campo: valor.includes('nota') ? 'nota' : 'data', direcao: valor === 'recentes' || valor === 'maior_nota' ? 'desc' : 'asc' })
              }}>
              <option value="recentes">Mais recentes</option>
              <option value="antigos">Mais antigos</option>
              <option value="maior_nota">Maior nota</option>
              <option value="menor_nota">Menor nota</option>
              <option value="coluna" disabled>Ordenado pela tabela</option>
            </select>
          </label>

          <label className="field">
            Buscar por número, modalidade ou área
            <input
              value={pesquisa}
              onChange={(evento) => setPesquisa(evento.target.value)}
              placeholder="Ex.: 15, Direito, Comportamental"
            />
          </label>
        </div>

        <p className="note">
          {filtradas.length} relatório(s) encontrado(s).
          Entrevistas não avaliadas permanecem acessíveis somente pelo histórico. Clique nos cabeçalhos para ordenar.
        </p>

        {filtradas.length === 0 ? (
          <div className="empty-state">{entrevistas.length === 0 ? <><p>Você ainda não tem entrevistas avaliadas.</p><Link className="button button--primary" to="/entrevistas/nova">Iniciar uma entrevista</Link></> : 'Nenhum relatório encontrado para os filtros selecionados.'}</div>
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
                    <td>{dataFormatada(item.data_fim ?? item.data_inicio)}</td>
                    <td>
                      {item.pontuacao_final === null
                        ? '-'
                        : `${item.pontuacao_final.toFixed(2)}/10`}
                    </td>
                    <td>
                      <Link to={`/relatorios/${item.id}`}>Abrir relatório</Link>
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
