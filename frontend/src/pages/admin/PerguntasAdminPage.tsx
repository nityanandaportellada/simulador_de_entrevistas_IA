import { useEffect, useState } from 'react'
import { Loading } from '../../components/Loading'
import { adminService } from '../../services/adminService'
import type { Pergunta } from '../../types/pergunta'

export function PerguntasAdminPage() {
  const [items, setItems] = useState<Pergunta[]>([])
  const [loading, setLoading] = useState(true)

  async function carregar() {
    setLoading(true)
    try {
      setItems(await adminService.perguntas())
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { void carregar() }, [])

  async function alternar(item: Pergunta) {
    if (item.ativa) await adminService.inativarPergunta(item.id)
    else await adminService.ativarPergunta(item.id)
    await carregar()
  }

  if (loading) return <Loading />

  return (
    <div>
      <div className="page-heading">
        <div>
          <h1>Gestão de perguntas</h1>
          <p>Visualize, organize e controle as perguntas utilizadas nas entrevistas.</p>
        </div>
      </div>

      <section className="panel">
        <div className="table-wrap">
          <table>
            <thead>
              <tr><th>ID</th><th>Pergunta</th><th>Tipo</th><th>Competência</th><th>Ordem</th><th>Peso</th><th>STAR</th><th>Status</th><th>Ação</th></tr>
            </thead>
            <tbody>
              {items.map((item) => (
                <tr key={item.id}>
                  <td>{item.id}</td>
                  <td className="table-text">{item.texto}</td>
                  <td>{item.tipo_entrevista_id}</td>
                  <td>{item.competencia_id}</td>
                  <td>{item.ordem ?? '-'}</td>
                  <td>{item.peso}</td>
                  <td>{item.usa_star ? 'Sim' : 'Não'}</td>
                  <td>{item.ativa ? 'Ativa' : 'Inativa'}</td>
                  <td><button className="button button--small button--outline" onClick={() => alternar(item)}>{item.ativa ? 'Inativar' : 'Ativar'}</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <div className="note">
        O formulário completo de criação/edição será implementado na próxima subetapa, usando os endpoints já validados.
      </div>
    </div>
  )
}
