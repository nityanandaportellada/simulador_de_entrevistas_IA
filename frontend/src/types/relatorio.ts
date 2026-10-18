
import type { DesempenhoCriterio, DestaqueCriterio } from './avaliacao'
import type { StatusEntrevista } from './entrevista'

export interface NotaCriterio {
  avaliacao_id: number
  resposta_id: number
  pergunta_id: number
  criterio_id: number
  criterio: string
  criterio_descricao: string | null
  ordem_criterio: number | null
  nota: number
  observacao: string | null
  peso_criterio: number
  peso_pergunta: number
}

export interface AvaliacaoResposta {
  id: number
  pontuacao: number | null
  pontos_fortes: string[]
  pontos_melhoria: string[]
  feedback: string | null
  modelo_ia: string | null
  data_avaliacao: string | null
  criterios: NotaCriterio[]
}

export interface RespostaRelatorio {
  resposta_id: number
  pergunta_id: number
  pergunta: string
  exemplo_esperado: string | null
  // Perguntas tecnicas podem nao ter competencia vinculada.
  competencia_id: number | null
  competencia: string | null
  usa_star: boolean | null
  peso_pergunta: number
  ordem_pergunta: number | null
  area_tecnica_id: number | null
  area_tecnica: string | null
  subarea_tecnica_id: number | null
  subarea_tecnica: string | null
  texto_resposta: string
  tempo_resposta: number | null
  data_resposta: string | null
  avaliacao: AvaliacaoResposta | null
}

export interface EntrevistaRelatorio {
  id: number
  usuario_id: number
  tipo_entrevista_id: number
  tipo_entrevista: string | null
  tipo_entrevista_descricao: string | null
  area_tecnica_id: number | null
  area_tecnica: string | null
  subarea_tecnica_id: number | null
  subarea_tecnica: string | null
  data_inicio: string
  data_fim: string | null
  status: StatusEntrevista
  pontuacao_final: number | null
  observacoes: string | null
}

export interface DestaquesRelatorio {
  melhor_criterio: DestaqueCriterio | null
  criterio_a_desenvolver: DestaqueCriterio | null
}

export interface RelatorioEntrevista {
  entrevista: EntrevistaRelatorio
  quantidade_perguntas: number
  quantidade_respostas: number
  quantidade_avaliacoes: number
  classificacao: string | null
  desempenho_criterios: DesempenhoCriterio[]
  destaques: DestaquesRelatorio
  respostas: RespostaRelatorio[]
}
