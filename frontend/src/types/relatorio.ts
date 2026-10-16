import type { Entrevista } from './entrevista'
import type { DesempenhoCriterio, DestaqueCriterio } from './avaliacao'

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
  pontuacao: number
  pontos_fortes: string[]
  pontos_melhoria: string[]
  feedback: string
  modelo_ia: string
  data_avaliacao: string
  criterios: NotaCriterio[]
}

export interface RespostaRelatorio {
  resposta_id: number
  pergunta_id: number
  pergunta: string
  competencia_id: number
  usa_star: boolean
  peso_pergunta: number
  texto_resposta: string
  tempo_resposta: number | null
  data_resposta: string
  avaliacao: AvaliacaoResposta | null
}

export interface DestaquesRelatorio {
  melhor_criterio: DestaqueCriterio | null
  criterio_a_desenvolver: DestaqueCriterio | null
}

export interface RelatorioEntrevista {
  entrevista: Entrevista
  quantidade_respostas: number
  quantidade_avaliacoes: number
  classificacao: string
  desempenho_criterios: DesempenhoCriterio[]
  destaques: DestaquesRelatorio
  respostas: RespostaRelatorio[]
}
