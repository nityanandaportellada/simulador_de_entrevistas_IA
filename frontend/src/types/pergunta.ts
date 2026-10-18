export interface Pergunta {
  id: number
  tipo_entrevista_id: number
  competencia_id: number
  texto: string
  exemplo_esperado: string | null
  ordem: number | null
  ativa: boolean
  peso: number
  usa_star: boolean
  data_criacao: string | null
  area_tecnica_id: number | null
  subarea_tecnica_id: number | null
}

export interface PerguntaRequest {
  tipo_entrevista_id: number
  competencia_id: number
  texto: string
  exemplo_esperado?: string | null
  ordem?: number | null
  peso: number
  usa_star: boolean
  area_tecnica_id?: number | null
  subarea_tecnica_id?: number | null
}

export type AtivarPerguntaResponse = Pergunta