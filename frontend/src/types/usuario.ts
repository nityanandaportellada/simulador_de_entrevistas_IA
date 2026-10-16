export type PerfilUsuario = 'estudante' | 'administrador'

export interface Usuario {
  id: number
  nome: string
  email: string
  perfil: PerfilUsuario
  ativo: boolean
  data_criacao: string
  ultimo_acesso: string | null
}

export interface UsuarioResumo {
  id: number
  nome: string
  email: string
  perfil: PerfilUsuario
  ativo: boolean
}

export interface AlterarPerfilRequest {
  perfil: PerfilUsuario
}

export interface AlterarPerfilResponse {
  mensagem: string
  usuario: UsuarioResumo
}

export interface MensagemResponse {
  mensagem: string
}
