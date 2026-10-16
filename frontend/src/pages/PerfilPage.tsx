import { useAuth } from '../contexts/AuthContext'

export function PerfilPage() {
  const { usuario } = useAuth()

  return (
    <div>
      <div className="page-heading">
        <div>
          <h1>Perfil</h1>
          <p>Informações da sua conta no Simulador de Entrevistas FESP-PR.</p>
        </div>
      </div>

      <section className="panel profile-card">
        <div className="avatar avatar--large">{usuario?.nome?.charAt(0).toUpperCase()}</div>
        <div>
          <h2>{usuario?.nome}</h2>
          <p>{usuario?.email}</p>
          <span className="status status--avaliada">{usuario?.perfil}</span>
        </div>
      </section>
    </div>
  )
}
