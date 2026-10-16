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
}

export interface CriarEntrevistaRequest {
  tipo_entrevista_id: number
}

export interface FinalizarEntrevistaResponse {
  entrevista_id: number
  status: 'finalizada'
  data_fim: string
  mensagem: string
}

export interface Resposta {
  id: number
  entrevista_id: number
  pergunta_id: number
  texto_resposta: string
  tempo_resposta: number | null
  data_resposta: string
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
