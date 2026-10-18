export interface TipoEntrevista {
  id: number
  nome: string
  ativo: boolean
  usa_area_tecnica: boolean
}

export interface TipoEntrevistaRequest {
  nome: string
}

export interface AreaTecnica {
  id: number
  nome: string
  descricao: string | null
  ativo: boolean
  ordem: number | null
  data_criacao: string | null
}

export interface SubareaTecnica {
  id: number
  area_tecnica_id: number
  nome: string
  descricao: string | null
  eh_geral: boolean
  ativo: boolean
  ordem: number | null
  data_criacao: string | null
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
  ordem: number | null
  ativo: boolean
}

export interface CriterioAvaliacaoRequest {
  nome: string
  descricao?: string | null
  peso: number
  ordem?: number | null
}