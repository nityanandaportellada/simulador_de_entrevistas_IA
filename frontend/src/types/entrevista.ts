export type StatusEntrevista =
  | 'em_andamento'
  | 'finalizada'
  | 'em_analise'
  | 'avaliada'
  | 'erro_analise'
  | 'cancelada'

export interface Entrevista {
  id: number
  usuario_id: number
  tipo_entrevista_id: number
  data_inicio: string
  data_fim: string | null
  status: StatusEntrevista
  pontuacao_final: number | null
  observacoes: string | null
  tipo_entrevista_nome_aplicado: string | null
  tipo_entrevista_descricao_aplicada: string | null
  area_tecnica_id: number | null
  subarea_tecnica_id: number | null
  area_tecnica_nome_aplicado: string | null
  subarea_tecnica_nome_aplicado: string | null
}

export interface CriarEntrevistaRequest {
  tipo_entrevista_id: number
  area_tecnica_id?: number | null
  subarea_tecnica_id?: number | null
}

export interface EntrevistaPergunta {
  id: number
  entrevista_id: number
  pergunta_id: number
  pergunta_texto_aplicado: string
  exemplo_esperado_aplicado: string | null
  competencia_id_aplicada: number
  competencia_nome_aplicada: string
  area_tecnica_id_aplicada: number | null
  area_tecnica_nome_aplicada: string | null
  subarea_tecnica_id_aplicada: number | null
  subarea_tecnica_nome_aplicada: string | null
  peso_pergunta_aplicado: number
  usa_star_aplicado: boolean
  ordem_pergunta_aplicada: number | null
  data_aplicacao: string | null
}

export interface FinalizarEntrevistaResponse {
  entrevista_id: number
  status: 'finalizada'
  data_fim: string
  quantidade_perguntas: number
  quantidade_respostas: number
  mensagem: string
}

export interface Resposta {
  id: number
  entrevista_id: number
  pergunta_id: number
  texto_resposta: string
  tempo_resposta: number | null
  data_resposta: string | null
  pergunta_texto_aplicado: string | null
  exemplo_esperado_aplicado: string | null
  competencia_id_aplicada: number | null
  competencia_nome_aplicada: string | null
  peso_pergunta_aplicado: number | null
  usa_star_aplicado: boolean | null
  ordem_pergunta_aplicada: number | null
}

export interface CriarRespostaRequest {
  pergunta_id: number
  texto_resposta: string
  tempo_resposta?: number | null
}

export interface CriarRespostaResponse {
  id: number
  entrevista_id: number
  pergunta_id: number
  mensagem: string
}