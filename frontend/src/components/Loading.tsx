
/** Indica o carregamento também para quem utiliza leitor de tela. */
export function Loading({ text = 'Carregando...' }: { text?: string }) {
  return (
    <div className="loading" role="status" aria-live="polite" aria-atomic="true">
      <div className="spinner" aria-hidden="true" />
      <span>{text}</span>
    </div>
  )
}
