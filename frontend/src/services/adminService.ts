
import { apiGet, apiPost, apiPut } from './api'
import type {
  AlterarPerfilRequest,
  AlterarPerfilResponse,
  MensagemResponse,
  Usuario,
  PerfilUsuario
} from '../types/usuario'
import type {
  AreaTecnica,
  Competencia,
  CompetenciaRequest,
  CriterioAvaliacao,
  CriterioAvaliacaoRequest,
  SubareaTecnica,
  TipoEntrevista,
  TipoEntrevistaRequest
} from '../types/catalogos'
import type {
  AtivarPerguntaResponse,
  Pergunta,
  PerguntaRequest
} from '../types/pergunta'

export interface NovoUsuarioAdmin {
  nome: string
  email: string
  senha: string
  perfil: PerfilUsuario
}

export interface EditarUsuarioAdmin {
  nome: string
  email: string
}

export interface RedefinirSenhaUsuarioAdmin {
  nova_senha: string
  senha_atual?: string
}

export const adminService = {
  usuarios: () => apiGet<Usuario[]>('/usuarios'),
  criarUsuario: (dados: NovoUsuarioAdmin) =>
    apiPost<Usuario, NovoUsuarioAdmin>('/usuarios', dados),
  editarUsuario: (id: number, dados: EditarUsuarioAdmin) =>
    apiPut<Usuario, EditarUsuarioAdmin>(`/usuarios/${id}`, dados),
  redefinirSenhaUsuario: (id: number, dados: RedefinirSenhaUsuarioAdmin) =>
    apiPut<void, RedefinirSenhaUsuarioAdmin>(`/usuarios/${id}/senha`, dados),
  alterarPerfil: (id: number, body: AlterarPerfilRequest) =>
    apiPut<AlterarPerfilResponse, AlterarPerfilRequest>(
      `/usuarios/${id}/perfil`,
      body
    ),
  inativarUsuario: (id: number) =>
    apiPut<MensagemResponse>(`/usuarios/${id}/inativar`),
  ativarUsuario: (id: number) =>
    apiPut<MensagemResponse>(`/usuarios/${id}/ativar`),

  tipos: () =>
    apiGet<TipoEntrevista[]>('/tipos-entrevista'),
  criarTipo: (body: TipoEntrevistaRequest) =>
    apiPost<TipoEntrevista, TipoEntrevistaRequest>(
      '/tipos-entrevista',
      body
    ),
  editarTipo: (id: number, body: TipoEntrevistaRequest) =>
    apiPut<TipoEntrevista, TipoEntrevistaRequest>(
      `/tipos-entrevista/${id}`,
      body
    ),
  inativarTipo: (id: number) =>
    apiPut<TipoEntrevista>(`/tipos-entrevista/${id}/inativar`),
  ativarTipo: (id: number) =>
    apiPut<TipoEntrevista>(`/tipos-entrevista/${id}/ativar`),

  competencias: () =>
    apiGet<Competencia[]>('/competencias'),
  criarCompetencia: (body: CompetenciaRequest) =>
    apiPost<Competencia, CompetenciaRequest>(
      '/competencias',
      body
    ),
  editarCompetencia: (id: number, body: CompetenciaRequest) =>
    apiPut<Competencia, CompetenciaRequest>(
      `/competencias/${id}`,
      body
    ),
  inativarCompetencia: (id: number) =>
    apiPut<Competencia>(`/competencias/${id}/inativar`),
  ativarCompetencia: (id: number) =>
    apiPut<Competencia>(`/competencias/${id}/ativar`),

  criterios: () =>
    apiGet<CriterioAvaliacao[]>('/criterios'),
  criarCriterio: (body: CriterioAvaliacaoRequest) =>
    apiPost<CriterioAvaliacao, CriterioAvaliacaoRequest>(
      '/criterios',
      body
    ),
  editarCriterio: (id: number, body: CriterioAvaliacaoRequest) =>
    apiPut<CriterioAvaliacao, CriterioAvaliacaoRequest>(
      `/criterios/${id}`,
      body
    ),
  inativarCriterio: (id: number) =>
    apiPut<CriterioAvaliacao>(`/criterios/${id}/inativar`),
  ativarCriterio: (id: number) =>
    apiPut<CriterioAvaliacao>(`/criterios/${id}/ativar`),

  areas: () =>
    apiGet<AreaTecnica[]>('/areas-tecnicas?somente_ativas=false'),

  subareas: () =>
    apiGet<SubareaTecnica[]>('/subareas-tecnicas?somente_ativas=false'),

  perguntas: () =>
    apiGet<Pergunta[]>('/perguntas?somente_ativas=false'),

  criarPergunta: (body: PerguntaRequest) =>
    apiPost<Pergunta, PerguntaRequest>(
      '/perguntas',
      body
    ),

  editarPergunta: (id: number, body: PerguntaRequest) =>
    apiPut<Pergunta, PerguntaRequest>(
      `/perguntas/${id}`,
      body
    ),

  inativarPergunta: (id: number) =>
    apiPut<Pergunta>(
      `/perguntas/${id}/inativar`
    ),

  ativarPergunta: (id: number) =>
    apiPut<AtivarPerguntaResponse>(
      `/perguntas/${id}/ativar`
    )
}
