import { apiGet, apiPost } from './api'
import type { AreaTecnica, SubareaTecnica, TipoEntrevista } from '../types/catalogos'
import type { Pergunta } from '../types/pergunta'
import type {
  CriarEntrevistaRequest,
  CriarRespostaRequest,
  CriarRespostaResponse,
  Entrevista,
  EntrevistaPergunta,
  FinalizarEntrevistaResponse,
  Resposta
} from '../types/entrevista'
import type { AnaliseEntrevistaResponse } from '../types/avaliacao'
import type { RelatorioEntrevista } from '../types/relatorio'
import type { EvolucaoCriterios, EvolucaoPontuacao, ItemHistorico, ResumoHistorico } from '../types/historico'

export const studentService = {
  listarTipos: () => apiGet<TipoEntrevista[]>('/tipos-entrevista?somente_ativos=true'),
  listarAreas: () => apiGet<AreaTecnica[]>('/areas-tecnicas?somente_ativas=true'),
  listarSubareas: (areaId: number) =>
    apiGet<SubareaTecnica[]>(`/areas-tecnicas/${areaId}/subareas?somente_ativas=true`),
  listarPerguntas: () => apiGet<Pergunta[]>('/perguntas'),
  criarEntrevista: (body: CriarEntrevistaRequest) =>
    apiPost<Entrevista, CriarEntrevistaRequest>('/entrevistas', body),
  buscarEntrevista: (id: number) => apiGet<Entrevista>(`/entrevistas/${id}`),
  listarPerguntasEntrevista: (id: number) => apiGet<EntrevistaPergunta[]>(`/entrevistas/${id}/perguntas`),
  listarRespostas: (id: number) => apiGet<Resposta[]>(`/entrevistas/${id}/respostas`),
  responder: (id: number, body: CriarRespostaRequest) =>
    apiPost<CriarRespostaResponse, CriarRespostaRequest>(`/entrevistas/${id}/respostas`, body),
  finalizar: (id: number) => apiPost<FinalizarEntrevistaResponse>(`/entrevistas/${id}/finalizar`),
  analisar: (id: number) => apiPost<AnaliseEntrevistaResponse>(`/analise/entrevistas/${id}`),
  relatorio: (id: number) => apiGet<RelatorioEntrevista>(`/relatorios/entrevistas/${id}`),
  historico: () => apiGet<ItemHistorico[]>('/historico'),
  resumo: () => apiGet<ResumoHistorico>('/historico/resumo'),
  evolucao: () => apiGet<EvolucaoPontuacao[]>('/historico/evolucao'),
  evolucaoCriterios: () => apiGet<EvolucaoCriterios[]>('/historico/evolucao-criterios')
}