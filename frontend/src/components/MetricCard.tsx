import type { ReactNode } from 'react'

interface Props {
  label: string
  value: ReactNode
  icon?: ReactNode
  helper?: string
}

export function MetricCard({ label, value, icon, helper }: Props) {
  return (
    <section className="metric-card">
      <div className="metric-card__icon">{icon}</div>
      <div>
        <div className="metric-card__label">{label}</div>
        <div className="metric-card__value">{value}</div>
        {helper && <div className="metric-card__helper">{helper}</div>}
      </div>
    </section>
  )
}
