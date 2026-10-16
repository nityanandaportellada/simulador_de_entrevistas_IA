import { useEffect, useState } from 'react'
import { adminService } from '../../services/adminService'
import type { Usuario } from '../../types/usuario'
import { Loading } from '../../components/Loading'

export function UsuariosAdminPage() {
  const [items, setItems] = useState<Usuario[]>([])
  const [loading, setLoading] = useState(true)

  async function carregar() {
    setLoading(true)
    try {
      setItems(await adminService.usuarios())
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { void carregar() }, [])

  async function alternarAtivo(item: Usuario) {
    if (item.ativo) await adminService.inativarUsuario(item.id)
    else await adminService.ativarUsuario(item.id)
    await carregar()
  }

  async function alternarPerfil(item: Usuario) {
    await adminService.alterarPerfil(item.id, {
      perfil: item.perfil === 'administrador' ? 'estudante' : 'administrador'
    })
    await carregar()
  }

  if (loading) return <Loading />

  return (
    <div>
      <div className="page-heading">
        <div>
          <h1>Gestão de usuários</h1>
          <p>Gerencie perfis e situação de acesso dos usuários.</p>
        </div>
      </div>

      <section className="panel">
        <div className="table-wrap">
          <table>
            <thead><tr><th>ID</th><th>Nome</th><th>E-mail</th><th>Perfil</th><th>Ativo</th><th>Ações</th></tr></thead>
            <tbody>
              {items.map((item) => (
                <tr key={item.id}>
                  <td>{item.id}</td>
                  <td>{item.nome}</td>
                  <td>{item.email}</td>
                  <td><span className="pill">{item.perfil}</span></td>
                  <td><span className={`status ${item.ativo ? 'status--avaliada' : 'status--erro_analise'}`}>{item.ativo ? 'Ativo' : 'Inativo'}</span></td>
                  <td>
                    <div className="button-row">
                      <button className="button button--small button--outline" onClick={() => alternarPerfil(item)}>
                        {item.perfil === 'administrador' ? 'Tornar estudante' : 'Tornar admin'}
                      </button>
                      <button className="button button--small button--ghost" onClick={() => alternarAtivo(item)}>
                        {item.ativo ? 'Inativar' : 'Ativar'}
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  )
}
