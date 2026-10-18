import type { StatusEntrevista } from './entrevista'

export interface ItemHistorico {
  id: number
  tipo_entrevista_id: number
  tipo_entrevista: string | null
  area_tecnica_id: number | null
  area_tecnica: string | null
  subarea_tecnica_id: number | null
  subarea_tecnica: string | null
  data_inicio: string
  data_fim: string | null
  status: StatusEntrevista
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
  tipo_entrevista_id: number
  tipo_entrevista: string | null
  area_tecnica_id: number | null
  area_tecnica: string | null
  subarea_tecnica_id: number | null
  subarea_tecnica: string | null
}

export interface DesempenhoCriterio {
  criterio_id: number
  criterio: string
  criterio_descricao: string | null
  ordem_criterio: number | null
  media: number
  peso: number
  quantidade_avaliacoes: number
}

export interface EvolucaoCriterios {
  entrevista_id: number
  data: string
  tipo_entrevista_id: number
  tipo_entrevista: string | null
  area_tecnica_id: number | null
  area_tecnica: string | null
  subarea_tecnica_id: number | null
  subarea_tecnica: string | null
  criterios: DesempenhoCriterio[]
}