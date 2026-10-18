import { useEffect, useState } from 'react'
import { Loading } from '../../components/Loading'
import { adminService } from '../../services/adminService'
import type {
  AreaTecnica,
  Competencia,
  SubareaTecnica,
  TipoEntrevista
} from '../../types/catalogos'
import type { Pergunta } from '../../types/pergunta'

export function PerguntasAdminPage() {
  const [items, setItems] = useState<Pergunta[]>([])
  const [tipos, setTipos] = useState<TipoEntrevista[]>([])
  const [competencias, setCompetencias] = useState<Competencia[]>([])
  const [areas, setAreas] = useState<AreaTecnica[]>([])
  const [subareas, setSubareas] = useState<SubareaTecnica[]>([])
  const [loading, setLoading] = useState(true)

  async function carregar() {
    setLoading(true)

    try {
      const [
        perguntas,
        tiposRecebidos,
        competenciasRecebidas,
        areasRecebidas,
        subareasRecebidas
      ] = await Promise.all([
        adminService.perguntas(),
        adminService.tipos(),
        adminService.competencias(),
        adminService.areas(),
        adminService.subareas()
      ])

      setItems(perguntas)
      setTipos(tiposRecebidos)
      setCompetencias(competenciasRecebidas)
      setAreas(areasRecebidas)
      setSubareas(subareasRecebidas)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void carregar()
  }, [])

  async function alternar(item: Pergunta) {
    if (item.ativa) {
      await adminService.inativarPergunta(item.id)
    } else {
      await adminService.ativarPergunta(item.id)
    }

    await carregar()
  }

  function nomeTipo(id: number) {
    return tipos.find((tipo) => tipo.id === id)?.nome ?? `#${id}`
  }

  function nomeCompetencia(id: number) {
    return competencias.find(
      (competencia) => competencia.id === id
    )?.nome ?? `#${id}`
  }

  function contextoTecnico(item: Pergunta) {
    if (!item.area_tecnica_id) {
      return '-'
    }

    const area =
      areas.find(
        (registro) => registro.id === item.area_tecnica_id
      )?.nome ?? `Área #${item.area_tecnica_id}`

    if (!item.subarea_tecnica_id) {
      return area
    }

    const subarea =
      subareas.find(
        (registro) => registro.id === item.subarea_tecnica_id
      )?.nome ?? `Subárea #${item.subarea_tecnica_id}`

    return `${area} / ${subarea}`
  }

  if (loading) return <Loading />

  return (
    <div>
      <div className="page-heading">
        <div>
          <h1>Gestão de perguntas</h1>
          <p>
            Visualize, organize e controle as perguntas utilizadas nas entrevistas.
          </p>
        </div>
      </div>

      <section className="panel">
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>ID</th>
                <th>Pergunta</th>
                <th>Tipo</th>
                <th>Competência</th>
                <th>Contexto técnico</th>
                <th>Ordem</th>
                <th>Peso</th>
                <th>STAR</th>
                <th>Status</th>
                <th>Ação</th>
              </tr>
            </thead>

            <tbody>
              {items.map((item) => (
                <tr key={item.id}>
                  <td>{item.id}</td>

                  <td className="table-text">
                    {item.texto}
                  </td>

                  <td>
                    {nomeTipo(item.tipo_entrevista_id)}
                  </td>

                  <td>
                    {nomeCompetencia(item.competencia_id)}
                  </td>

                  <td>
                    {contextoTecnico(item)}
                  </td>

                  <td>
                    {item.ordem ?? '-'}
                  </td>

                  <td>
                    {item.peso}
                  </td>

                  <td>
                    {item.usa_star ? 'Sim' : 'Não'}
                  </td>

                  <td>
                    {item.ativa ? 'Ativa' : 'Inativa'}
                  </td>

                  <td>
                    <button
                      className="button button--small button--outline"
                      onClick={() => alternar(item)}
                    >
                      {item.ativa ? 'Inativar' : 'Ativar'}
                    </button>
                  </td>
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