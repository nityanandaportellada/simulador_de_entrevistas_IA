import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Loading } from '../components/Loading'
import { studentService } from '../services/studentService'
import type { ItemHistorico } from '../types/historico'

export function RelatoriosPage() {
  const [items, setItems] = useState<ItemHistorico[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    studentService.historico()
      .then((dados) => setItems(dados.filter((x) => x.status === 'avaliada')))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <Loading />

  return (
    <div>
      <div className="page-heading">
        <div>
          <h1>Relatórios</h1>
          <p>Acesse os relatórios das entrevistas avaliadas.</p>
        </div>
      </div>

      <section className="panel">
        <div className="table-wrap">
          <table>
            <thead>
              <tr><th>Entrevista</th><th>Data</th><th>Pontuação</th><th>Ação</th></tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr key={item.id}>
                  <td>Entrevista #{item.id}</td>
                  <td>{item.data_inicio}</td>
                  <td>{item.pontuacao_final ?? '-'}</td>
                  <td><Link to={`/relatorios/${item.id}`}>Abrir relatório</Link></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  )
}
