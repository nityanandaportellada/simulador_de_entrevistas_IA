import { useEffect, useState } from 'react'
import { adminService } from '../../services/adminService'
import { Loading } from '../../components/Loading'
import type { Competencia, CriterioAvaliacao, TipoEntrevista } from '../../types/catalogos'

type Mode = 'tipos' | 'competencias' | 'criterios'

export function CatalogoAdminPage({ mode }: { mode: Mode }) {
  const [items, setItems] = useState<Array<TipoEntrevista | Competencia | CriterioAvaliacao>>([])
  const [loading, setLoading] = useState(true)

  async function carregar() {
    setLoading(true)
    try {
      if (mode === 'tipos') setItems(await adminService.tipos())
      if (mode === 'competencias') setItems(await adminService.competencias())
      if (mode === 'criterios') setItems(await adminService.criterios())
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { void carregar() }, [mode])

  async function alternar(item: any) {
    if (mode === 'tipos') {
      if (item.ativo) await adminService.inativarTipo(item.id)
      else await adminService.ativarTipo(item.id)
    }
    if (mode === 'competencias') {
      if (item.ativo) await adminService.inativarCompetencia(item.id)
      else await adminService.ativarCompetencia(item.id)
    }
    if (mode === 'criterios') {
      if (item.ativo) await adminService.inativarCriterio(item.id)
      else await adminService.ativarCriterio(item.id)
    }
    await carregar()
  }

  if (loading) return <Loading />

  const titulo =
    mode === 'tipos' ? 'Tipos de entrevista' :
    mode === 'competencias' ? 'Competências' :
    'Critérios de avaliação'

  return (
    <div>
      <div className="page-heading">
        <div>
          <h1>{titulo}</h1>
          <p>Gerencie os registros utilizados pelo simulador.</p>
        </div>
      </div>

      <section className="panel">
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>ID</th><th>Nome</th>
                {mode !== 'tipos' && <th>Descrição</th>}
                {mode === 'criterios' && <><th>Peso</th><th>Ordem</th></>}
                <th>Ativo</th><th>Ações</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item: any) => (
                <tr key={item.id}>
                  <td>{item.id}</td>
                  <td>{item.nome}</td>
                  {mode !== 'tipos' && <td>{item.descricao}</td>}
                  {mode === 'criterios' && <><td>{item.peso}</td><td>{item.ordem}</td></>}
                  <td>{item.ativo ? 'Sim' : 'Não'}</td>
                  <td>
                    <button className="button button--small button--outline" onClick={() => alternar(item)}>
                      {item.ativo ? 'Inativar' : 'Ativar'}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <div className="note">
        A criação e edição por formulário será a próxima subetapa da Fase 18, preservando o contrato já validado.
      </div>
    </div>
  )
}
