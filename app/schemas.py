"""
schemas.py

Schemas Pydantic utilizados pela API do
Simulador de Entrevistas.

Versão: 0.5
"""

from typing import Optional

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field
)


# ============================================================
# AUTENTICAÇÃO
# ============================================================

class LoginRequest(BaseModel):

    email: EmailStr

    senha: str = Field(
        min_length=8
    )


class TokenResponse(BaseModel):

    access_token: str

    token_type: str = "bearer"


# ============================================================
# USUÁRIOS
# ============================================================

class UsuarioCriar(BaseModel):

    nome: str = Field(
        min_length=2,
        max_length=150
    )

    email: EmailStr

    senha: str = Field(
        min_length=8,
        max_length=128
    )


class UsuarioAtualizar(BaseModel):

    nome: str = Field(
        min_length=2,
        max_length=150
    )

    email: EmailStr


class UsuarioResposta(BaseModel):

    model_config = ConfigDict(
        from_attributes=True
    )

    id: int

    nome: str

    email: str

    perfil: str

    ativo: bool

    data_criacao: Optional[str] = None

    ultimo_acesso: Optional[str] = None


class AlterarSenhaRequest(BaseModel):

    senha_atual: str

    nova_senha: str = Field(
        min_length=8,
        max_length=128
    )


class AlterarPerfilRequest(BaseModel):

    perfil: str


# ============================================================
# TIPOS DE ENTREVISTA
# ============================================================

class TipoEntrevistaCriar(BaseModel):

    nome: str = Field(
        min_length=2,
        max_length=100
    )


class TipoEntrevistaAtualizar(BaseModel):

    nome: str = Field(
        min_length=2,
        max_length=100
    )


class TipoEntrevistaResposta(BaseModel):

    id: int

    nome: str

    ativo: bool


class TipoEntrevistaDetalheResposta(BaseModel):

    id: int

    nome: str

    ativo: bool

    quantidade_perguntas: int = Field(
        ge=0
    )

    quantidade_entrevistas: int = Field(
        ge=0
    )

    em_uso: bool


# ============================================================
# COMPETÊNCIAS
# ============================================================

class CompetenciaCriar(BaseModel):

    nome: str = Field(
        min_length=2,
        max_length=100
    )

    descricao: Optional[str] = Field(
        default=None,
        max_length=1000
    )


class CompetenciaAtualizar(BaseModel):

    nome: str = Field(
        min_length=2,
        max_length=100
    )

    descricao: Optional[str] = Field(
        default=None,
        max_length=1000
    )


class CompetenciaResposta(BaseModel):

    id: int

    nome: str

    descricao: Optional[str] = None

    ativo: bool


class CompetenciaDetalheResposta(BaseModel):

    id: int

    nome: str

    descricao: Optional[str] = None

    ativo: bool

    quantidade_perguntas: int = Field(
        ge=0
    )

    quantidade_perguntas_ativas: int = Field(
        ge=0
    )

    em_uso: bool


# ============================================================
# CRITÉRIOS DE AVALIAÇÃO
# ============================================================

class CriterioCriar(BaseModel):

    nome: str = Field(
        min_length=2,
        max_length=150
    )

    descricao: Optional[str] = Field(
        default=None,
        max_length=2000
    )

    peso: float = Field(
        gt=0
    )

    ordem: Optional[int] = Field(
        default=None,
        gt=0
    )


class CriterioAtualizar(BaseModel):

    nome: str = Field(
        min_length=2,
        max_length=150
    )

    descricao: Optional[str] = Field(
        default=None,
        max_length=2000
    )

    peso: float = Field(
        gt=0
    )

    ordem: Optional[int] = Field(
        default=None,
        gt=0
    )


class CriterioResposta(BaseModel):

    id: int

    nome: str

    descricao: Optional[str] = None

    peso: float

    ordem: Optional[int] = None

    ativo: bool


class CriterioDetalheResposta(
    CriterioResposta
):

    quantidade_avaliacoes: int = Field(
        ge=0
    )

    em_uso: bool


class PesoCriterioResumo(BaseModel):

    criterio_id: int

    criterio: str

    peso: float

    participacao_percentual: float


class ResumoPesosResposta(BaseModel):

    quantidade_criterios_ativos: int = Field(
        ge=0
    )

    soma_pesos_ativos: float

    sistema_pronto_para_avaliar: bool

    pesos_somam_um: bool

    distribuicao: list[PesoCriterioResumo]


# ============================================================
# PERGUNTAS
# ============================================================

class PerguntaCriar(BaseModel):

    tipo_entrevista_id: int

    competencia_id: int

    texto: str = Field(
        min_length=3
    )

    exemplo_esperado: Optional[str] = None

    ordem: Optional[int] = None

    peso: float = Field(
        default=1.0,
        gt=0
    )

    usa_star: bool = False


class PerguntaResposta(BaseModel):

    model_config = ConfigDict(
        from_attributes=True
    )

    id: int

    tipo_entrevista_id: Optional[int] = None

    competencia_id: Optional[int] = None

    texto: str

    exemplo_esperado: Optional[str] = None

    ordem: Optional[int] = None

    ativa: bool

    peso: float

    usa_star: bool

    data_criacao: Optional[str] = None


class PerguntaAtualizar(BaseModel):

    tipo_entrevista_id: int

    competencia_id: int

    texto: str = Field(
        min_length=3
    )

    exemplo_esperado: Optional[str] = None

    ordem: Optional[int] = None

    peso: float = Field(
        default=1.0,
        gt=0
    )

    usa_star: bool = False


# ============================================================
# ENTREVISTAS
# ============================================================

class EntrevistaCriar(BaseModel):

    tipo_entrevista_id: int


class EntrevistaResposta(BaseModel):

    model_config = ConfigDict(
        from_attributes=True
    )

    id: int

    usuario_id: int

    tipo_entrevista_id: Optional[int] = None

    data_inicio: Optional[str] = None

    data_fim: Optional[str] = None

    status: str

    pontuacao_final: Optional[float] = None

    observacoes: Optional[str] = None


# ============================================================
# RESPOSTAS DO ESTUDANTE
# ============================================================

class RespostaCriar(BaseModel):

    pergunta_id: int

    texto_resposta: str = Field(
        min_length=1
    )

    tempo_resposta: Optional[int] = Field(
        default=None,
        ge=0
    )


class RespostaDetalhe(BaseModel):

    model_config = ConfigDict(
        from_attributes=True
    )

    id: int

    entrevista_id: int

    pergunta_id: int

    texto_resposta: str

    tempo_resposta: Optional[int] = None

    data_resposta: Optional[str] = None