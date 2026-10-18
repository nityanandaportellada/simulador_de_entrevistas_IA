
import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { Loading } from '../components/Loading'
import { studentService } from '../services/studentService'
import type { ItemHistorico } from '../types/historico'

function dataFormatada(valor: string): string {
  const data = new Date(valor.includes('T') ? valor : `${valor.replace(' ', 'T')}Z`)
  return Number.isNaN(data.getTime()) ? valor : data.toLocaleDateString('pt-BR')
}

export function RelatoriosPage() {
  const [entrevistas, setEntrevistas] = useState<ItemHistorico[]>([])
  const [loading, setLoading] = useState(true)
  const [erro, setErro] = useState('')
  const [tentativa, setTentativa] = useState(0)
  const [tipoFiltro, setTipoFiltro] = useState('todos')
  const [pesquisa, setPesquisa] = useState('')
  const [ordenacao, setOrdenacao] = useState('recentes')

  useEffect(() => {
    let ativo = true
    setLoading(true)
    setErro('')

    studentService.historico()
      .then((dados) => {
        if (ativo) setEntrevistas(dados.filter((item) => item.status === 'avaliada'))
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

    return entrevistas.filter((item) => {
      if (tipoFiltro !== 'todos' && item.tipo_entrevista_id !== Number(tipoFiltro)) return false
      const conteudo = `${item.id} ${item.tipo_entrevista ?? ''} ${item.area_tecnica ?? ''} ${item.subarea_tecnica ?? ''}`.toLocaleLowerCase('pt-BR')
      return !termo || conteudo.includes(termo)
    }).sort((a, b) => {
      if (ordenacao === 'maior_nota') {
        return (b.pontuacao_final ?? -1) - (a.pontuacao_final ?? -1)
      }
      if (ordenacao === 'menor_nota') {
        return (a.pontuacao_final ?? 11) - (b.pontuacao_final ?? 11)
      }
      return ordenacao === 'antigos'
        ? a.data_inicio.localeCompare(b.data_inicio) || a.id - b.id
        : b.data_inicio.localeCompare(a.data_inicio) || b.id - a.id
    })
  }, [entrevistas, tipoFiltro, pesquisa, ordenacao])

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
            <select value={ordenacao} onChange={(evento) => setOrdenacao(evento.target.value)}>
              <option value="recentes">Mais recentes</option>
              <option value="antigos">Mais antigos</option>
              <option value="maior_nota">Maior nota</option>
              <option value="menor_nota">Menor nota</option>
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
          Entrevistas não avaliadas permanecem acessíveis somente pelo histórico.
        </p>

        {filtradas.length === 0 ? (
          <div className="empty-state">Nenhum relatório encontrado para os filtros selecionados.</div>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Entrevista</th>
                  <th>Modalidade</th>
                  <th>Área / subárea</th>
                  <th>Data</th>
                  <th>Pontuação</th>
                  <th>Ação</th>
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
