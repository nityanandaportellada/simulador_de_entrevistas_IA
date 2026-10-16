export interface DesempenhoCriterio {
  criterio_id: number
  criterio: string
  criterio_descricao: string | null
  ordem_criterio: number | null
  media: number
  peso: number
  quantidade_avaliacoes: number
}

export interface DestaqueCriterio {
  criterio: string
  media: number
}

export interface ResultadoFinalAnalise {
  entrevista_id: number
  pontuacao_final: number
  classificacao: string
  desempenho_criterios: DesempenhoCriterio[]
  melhor_criterio: DestaqueCriterio | null
  criterio_a_desenvolver: DestaqueCriterio | null
}

export interface AnaliseEntrevistaResponse {
  entrevista_id: number
  modo_analise: 'mock' | 'openai'
  modelo: string
  avaliacoes: number[]
  resultado_final: ResultadoFinalAnalise
}
