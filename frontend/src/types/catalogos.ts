export interface TipoEntrevista {
  id: number
  nome: string
  ativo: boolean
}

export interface TipoEntrevistaRequest {
  nome: string
}

export interface Competencia {
  id: number
  nome: string
  descricao: string | null
  ativo: boolean
}

export interface CompetenciaRequest {
  nome: string
  descricao?: string | null
}

export interface CriterioAvaliacao {
  id: number
  nome: string
  descricao: string | null
  peso: number
  ordem: number
  ativo: boolean
}

export interface CriterioAvaliacaoRequest {
  nome: string
  descricao?: string | null
  peso: number
  ordem: number
}
