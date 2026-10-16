import { useEffect, useState } from 'react'
import { BarChart3, ClipboardList, MessageSquareText, Target, Users } from 'lucide-react'
import { MetricCard } from '../components/MetricCard'
import { Loading } from '../components/Loading'
import { adminService } from '../services/adminService'

export function AdminDashboardPage() {
  const [counts, setCounts] = useState({ usuarios: 0, tipos: 0, competencias: 0, criterios: 0, perguntas: 0 })
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([
      adminService.usuarios(),
      adminService.tipos(),
      adminService.competencias(),
      adminService.criterios(),
      adminService.perguntas()
    ])
      .then(([u, t, c, cr, p]) =>
        setCounts({
          usuarios: u.length,
          tipos: t.length,
          competencias: c.length,
          criterios: cr.length,
          perguntas: p.length
        })
      )
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <Loading />

  return (
    <div>
      <div className="page-heading">
        <div>
          <h1>Dashboard administrativo</h1>
          <p>Visão geral dos cadastros disponíveis no backend.</p>
        </div>
      </div>

      <div className="metric-grid metric-grid--5">
        <MetricCard label="Usuários" value={counts.usuarios} icon={<Users />} />
        <MetricCard label="Tipos" value={counts.tipos} icon={<ClipboardList />} />
        <MetricCard label="Competências" value={counts.competencias} icon={<Target />} />
        <MetricCard label="Critérios" value={counts.criterios} icon={<BarChart3 />} />
        <MetricCard label="Perguntas" value={counts.perguntas} icon={<MessageSquareText />} />
      </div>

      <section className="panel">
        <h2>Administração FESP-PR</h2>
        <p>
          Utilize o menu lateral para gerenciar usuários, tipos de entrevista,
          competências, critérios de avaliação e perguntas.
        </p>
      </section>
    </div>
  )
}
