import logo from '../assets/fesp-symbol.png'

export function Brand({ compact = false }: { compact?: boolean }) {
  return (
    <div className={`brand ${compact ? 'brand--compact' : ''}`}>
      <img className="brand__symbol" src={logo} alt="Símbolo FESP-PR" />
      <div>
        <div className="brand__title">FESP-PR</div>
        <div className="brand__subtitle">Simulador de Entrevistas</div>
      </div>
    </div>
  )
}
