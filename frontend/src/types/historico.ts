export interface ItemHistorico {
  id: number
  tipo_entrevista_id: number
  data_inicio: string
  data_fim: string | null
  status: string
  pontuacao_final: number | null
}

export interface ResumoHistorico {
  quantidade_total: number
  quantidade_avaliada: number
  media_pontuacoes: number | null
  melhor_pontuacao: number | null
  ultima_pontuacao: number | null
}

export interface EvolucaoPontuacao {
  entrevista_id: number
  data: string
  pontuacao: number
}

export interface EvolucaoCriterioSerie {
  criterio_id?: number
  criterio?: string
  [key: string]: unknown
}
