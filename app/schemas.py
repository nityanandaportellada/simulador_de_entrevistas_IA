
"""Schemas Pydantic usados para validar dados recebidos e devolvidos pela API."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, StringConstraints

# ============================================================
# AUTENTICAÇÃO
# ============================================================

class LoginRequest(BaseModel):
    """Valida o login e rejeita campos extras enviados pelo cliente."""
    model_config = ConfigDict(extra="forbid")
    email: EmailStr = Field(max_length=254)
    senha: str = Field(min_length=8, max_length=128)


class TokenResponse(BaseModel):
    """Retorna apenas o token de acesso; nunca inclui dados de senha."""
    model_config = ConfigDict(extra="forbid")
    access_token: str
    token_type: str = "bearer"


# ============================================================
# USUÁRIOS
# ============================================================

class UsuarioCriar(BaseModel):
    """Cadastro público; o perfil é sempre estudante no serviço de autenticação."""
    model_config = ConfigDict(extra="forbid")
    nome: Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=150)]
    email: EmailStr = Field(max_length=254)
    senha: str = Field(min_length=8, max_length=128)


class UsuarioAtualizar(BaseModel):
    """Permite alteração apenas do próprio nome e e-mail."""
    model_config = ConfigDict(extra="forbid")
    nome: Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=150)]
    email: EmailStr = Field(max_length=254)


class UsuarioResposta(BaseModel):
    """Exclui senha_hash e quaisquer outros campos internos das respostas HTTP."""
    model_config = ConfigDict(from_attributes=True, extra="forbid")
    id: int
    nome: str
    email: str
    perfil: str
    ativo: bool
    data_criacao: str | None = None
    ultimo_acesso: str | None = None


class AlterarSenhaRequest(BaseModel):
    """Recebe duas senhas sem aceitar campos administrativos adicionais."""
    model_config = ConfigDict(extra="forbid")
    senha_atual: str = Field(min_length=1, max_length=128)
    nova_senha: str = Field(min_length=8, max_length=128)


class AlterarPerfilRequest(BaseModel):
    """Restringe o perfil a um dos dois papéis existentes no banco."""
    model_config = ConfigDict(extra="forbid")
    perfil: Literal["estudante", "administrador"]


# ============================================================
# TIPOS DE ENTREVISTA
# ============================================================

class TipoEntrevistaCriar(BaseModel):
    # Valida o nome de um novo tipo de entrevista.
    nome: str = Field(min_length=2, max_length=100)


class TipoEntrevistaAtualizar(BaseModel):
    # Valida o nome usado ao editar um tipo de entrevista.
    nome: str = Field(min_length=2, max_length=100)


class TipoEntrevistaResposta(BaseModel):
    # Define os dados básicos devolvidos para um tipo de entrevista.
    id: int
    nome: str
    ativo: bool
    usa_area_tecnica: bool = False


class TipoEntrevistaDetalheResposta(BaseModel):
    # Acrescenta informações de uso ao detalhe de um tipo de entrevista.
    id: int
    nome: str
    ativo: bool
    usa_area_tecnica: bool = False
    quantidade_perguntas: int = Field(ge=0)
    quantidade_entrevistas: int = Field(ge=0)
    em_uso: bool


# ============================================================
# COMPETÊNCIAS
# ============================================================

class CompetenciaCriar(BaseModel):
    # Valida os dados usados no cadastro de uma competência.
    nome: str = Field(min_length=2, max_length=100)
    descricao: str | None = Field(default=None, max_length=1000)


class CompetenciaAtualizar(BaseModel):
    # Valida os dados usados para editar uma competência.
    nome: str = Field(min_length=2, max_length=100)
    descricao: str | None = Field(default=None, max_length=1000)


class CompetenciaResposta(BaseModel):
    # Define os dados básicos devolvidos para uma competência.
    id: int
    nome: str
    descricao: str | None = None
    ativo: bool


class CompetenciaDetalheResposta(BaseModel):
    # Mostra os dados da competência e quantas perguntas a utilizam.
    id: int
    nome: str
    descricao: str | None = None
    ativo: bool
    quantidade_perguntas: int = Field(ge=0)
    quantidade_perguntas_ativas: int = Field(ge=0)
    em_uso: bool


# ============================================================
# CRITÉRIOS DE AVALIAÇÃO
# ============================================================

class CriterioCriar(BaseModel):
    # Valida os dados usados para criar um critério de avaliação.
    nome: str = Field(min_length=2, max_length=150)
    descricao: str | None = Field(default=None, max_length=2000)
    peso: float = Field(gt=0)
    ordem: int | None = Field(default=None, gt=0)


class CriterioAtualizar(BaseModel):
    # Valida os dados usados para editar um critério de avaliação.
    nome: str = Field(min_length=2, max_length=150)
    descricao: str | None = Field(default=None, max_length=2000)
    peso: float = Field(gt=0)
    ordem: int | None = Field(default=None, gt=0)


class CriterioResposta(BaseModel):
    # Define os dados básicos devolvidos para um critério.
    id: int
    nome: str
    descricao: str | None = None
    peso: float
    ordem: int | None = None
    ativo: bool


class CriterioDetalheResposta(CriterioResposta):
    # Acrescenta ao critério a quantidade de avaliações que já o utilizaram.
    quantidade_avaliacoes: int = Field(ge=0)
    em_uso: bool


class PesoCriterioResumo(BaseModel):
    # Mostra o peso e a participação percentual de um critério ativo.
    criterio_id: int
    criterio: str
    peso: float
    participacao_percentual: float


class ResumoPesosResposta(BaseModel):
    # Resume a configuração atual dos pesos dos critérios ativos.
    quantidade_criterios_ativos: int = Field(ge=0)
    soma_pesos_ativos: float
    sistema_pronto_para_avaliar: bool
    pesos_somam_um: bool
    distribuicao: list[PesoCriterioResumo]


# ============================================================
# PERGUNTAS
# ============================================================

class PerguntaCriar(BaseModel):
    """Valida o cadastro de perguntas, inclusive aquelas de áreas técnicas."""
    tipo_entrevista_id: int = Field(gt=0)
    competencia_id: int | None = Field(default=None, gt=0)
    texto: str = Field(min_length=3)
    exemplo_esperado: str | None = None
    ordem: int | None = None
    peso: float = Field(default=1.0, gt=0)
    usa_star: bool = False
    area_tecnica_id: int | None = Field(default=None, gt=0)
    subarea_tecnica_id: int | None = Field(default=None, gt=0)
    codigo: str | None = Field(default=None, min_length=3, max_length=30)
    dificuldade: str | None = Field(default=None, pattern="^(basica|intermediaria|avancada)$")


class PerguntaResposta(BaseModel):
    """Define os dados que podem ser devolvidos ao consultar uma pergunta."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    tipo_entrevista_id: int | None = None
    competencia_id: int | None = None
    texto: str
    exemplo_esperado: str | None = None
    ordem: int | None = None
    ativa: bool
    peso: float
    usa_star: bool
    data_criacao: str | None = None
    area_tecnica_id: int | None = None
    subarea_tecnica_id: int | None = None
    codigo: str | None = None
    dificuldade: str | None = None


class PerguntaAtualizar(BaseModel):
    """Valida a edição de perguntas sem exigir competência em tipos técnicos."""
    tipo_entrevista_id: int = Field(gt=0)
    competencia_id: int | None = Field(default=None, gt=0)
    texto: str = Field(min_length=3)
    exemplo_esperado: str | None = None
    ordem: int | None = None
    peso: float = Field(default=1.0, gt=0)
    usa_star: bool = False
    area_tecnica_id: int | None = Field(default=None, gt=0)
    subarea_tecnica_id: int | None = Field(default=None, gt=0)
    codigo: str | None = Field(default=None, min_length=3, max_length=30)
    dificuldade: str | None = Field(default=None, pattern="^(basica|intermediaria|avancada)$")


# ============================================================
# ENTREVISTAS
# ============================================================

class EntrevistaCriar(BaseModel):
    """Recebe o tipo, o perfil e o contexto técnico para iniciar a entrevista."""
    tipo_entrevista_id: int = Field(gt=0)
    area_tecnica_id: int | None = Field(default=None, gt=0)
    subarea_tecnica_id: int | None = Field(default=None, gt=0)
    perfil_profissional: str | None = Field(default=None, pattern="^(estagio_trainee|junior|pleno|senior)$")


class EntrevistaResposta(BaseModel):
    # Define os dados básicos de uma entrevista devolvida pela API.
    model_config = ConfigDict(from_attributes=True)

    id: int
    usuario_id: int
    tipo_entrevista_id: int | None = None
    data_inicio: str | None = None
    data_fim: str | None = None
    status: str
    pontuacao_final: float | None = None
    observacoes: str | None = None
    perfil_profissional: str | None = None
    area_tecnica_id: int | None = None
    subarea_tecnica_id: int | None = None


# ============================================================
# RESPOSTAS DO ESTUDANTE
# ============================================================

class RespostaCriar(BaseModel):
    # Valida uma resposta enviada pelo estudante durante a entrevista.
    pergunta_id: int
    texto_resposta: str = Field(min_length=1)
    tempo_resposta: int | None = Field(default=None, ge=0)


class RespostaDetalhe(BaseModel):
    # Define os dados de uma resposta devolvida pela API.
    model_config = ConfigDict(from_attributes=True)

    id: int
    entrevista_id: int
    pergunta_id: int
    texto_resposta: str
    tempo_resposta: int | None = None
    data_resposta: str | None = None
