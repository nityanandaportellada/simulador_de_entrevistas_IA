
"""Modelos de dados usados pelo Simulador de Entrevistas."""

from dataclasses import dataclass

# ============================================================
# USUÁRIO
# ============================================================

@dataclass
class Usuario:
    """Guarda os dados de um usuário do sistema."""

    id: int | None = None
    nome: str = ""
    email: str = ""
    senha_hash: str = ""
    perfil: str = "estudante"
    ativo: bool = True
    data_criacao: str | None = None
    ultimo_acesso: str | None = None


# ============================================================
# TIPO DE ENTREVISTA
# ============================================================

@dataclass
class TipoEntrevista:
    """Guarda um tipo de entrevista e informa se ele usa área técnica."""

    id: int | None = None
    nome: str = ""
    descricao: str | None = None
    ativo: bool = True
    data_criacao: str | None = None
    usa_area_tecnica: bool = False


# ============================================================
# ÁREA TÉCNICA
# ============================================================

@dataclass
class AreaTecnica:
    """Representa uma área usada nas entrevistas técnicas."""

    id: int | None = None
    nome: str = ""
    descricao: str | None = None
    ativo: bool = True
    ordem: int | None = None
    data_criacao: str | None = None


# ============================================================
# SUBÁREA TÉCNICA
# ============================================================

@dataclass
class SubareaTecnica:
    """Representa uma subárea ligada a uma área técnica."""

    id: int | None = None
    area_tecnica_id: int | None = None
    nome: str = ""
    descricao: str | None = None
    eh_geral: bool = False
    ativo: bool = True
    ordem: int | None = None
    data_criacao: str | None = None


# ============================================================
# COMPETÊNCIA
# ============================================================

@dataclass
class Competencia:
    """Representa uma competência profissional ligada às perguntas."""

    id: int | None = None
    nome: str = ""
    descricao: str | None = None
    ativa: bool = True


# ============================================================
# CRITÉRIO DE AVALIAÇÃO
# ============================================================

@dataclass
class CriterioAvaliacao:
    """Representa um critério usado para avaliar as respostas."""

    id: int | None = None
    nome: str = ""
    descricao: str | None = None
    peso: float = 1.0
    ordem: int | None = None
    ativo: bool = True


# ============================================================
# PERGUNTA
# ============================================================

@dataclass
class Pergunta:
    """Guarda os dados de uma pergunta cadastrada no sistema."""

    id: int | None = None
    tipo_entrevista_id: int | None = None
    competencia_id: int | None = None
    texto: str = ""
    exemplo_esperado: str | None = None
    ordem: int | None = None
    ativa: bool = True
    peso: float = 1.0
    usa_star: bool = False
    data_criacao: str | None = None
    area_tecnica_id: int | None = None
    subarea_tecnica_id: int | None = None

    # Identificação e nível de dificuldade para a seleção automática.
    codigo: str | None = None
    dificuldade: str | None = None


# ============================================================
# ENTREVISTA
# ============================================================

@dataclass
class Entrevista:
    """Guarda os dados da entrevista e os nomes históricos aplicados nela."""

    id: int | None = None
    usuario_id: int | None = None
    tipo_entrevista_id: int | None = None
    data_inicio: str | None = None
    data_fim: str | None = None
    status: str = "em_andamento"
    pontuacao_final: float | None = None
    observacoes: str | None = None

    # Guarda o nome e a descrição do tipo como eram no momento da entrevista.
    tipo_entrevista_nome_aplicado: str | None = None
    tipo_entrevista_descricao_aplicada: str | None = None

    # Guarda a área e a subárea escolhidas para entrevistas técnicas.
    area_tecnica_id: int | None = None
    subarea_tecnica_id: int | None = None

    # Preserva os nomes da área e da subárea usados na entrevista.
    area_tecnica_nome_aplicado: str | None = None
    subarea_tecnica_nome_aplicado: str | None = None

    # Perfil profissional utilizado para definir a dificuldade das perguntas.
    perfil_profissional: str | None = None


# ============================================================
# PERGUNTA APLICADA À ENTREVISTA
# ============================================================

@dataclass
class EntrevistaPergunta:
    """Guarda a cópia da pergunta usada quando a entrevista foi iniciada."""

    id: int | None = None
    entrevista_id: int | None = None
    pergunta_id: int | None = None

    # Snapshot da pergunta.
    pergunta_texto_aplicado: str = ""
    exemplo_esperado_aplicado: str | None = None
    codigo_pergunta_aplicado: str | None = None
    dificuldade_aplicada: str | None = None

    # Snapshot da competência, que pode ser ausente nas perguntas técnicas.
    competencia_id_aplicada: int | None = None
    competencia_nome_aplicada: str | None = None

    # Snapshot da área técnica.
    area_tecnica_id_aplicada: int | None = None
    area_tecnica_nome_aplicada: str | None = None

    # Snapshot da subárea técnica.
    subarea_tecnica_id_aplicada: int | None = None
    subarea_tecnica_nome_aplicada: str | None = None

    # Configurações da pergunta usadas naquela entrevista.
    peso_pergunta_aplicado: float = 1.0
    usa_star_aplicado: bool = False
    ordem_pergunta_aplicada: int | None = None
    data_aplicacao: str | None = None


# ============================================================
# RESPOSTA
# ============================================================

@dataclass
class Resposta:
    """Guarda uma resposta do estudante e o snapshot da pergunta respondida."""

    id: int | None = None
    entrevista_id: int | None = None
    pergunta_id: int | None = None
    texto_resposta: str = ""
    tempo_resposta: int | None = None
    data_resposta: str | None = None

    # Snapshot histórico da pergunta no momento da resposta.
    pergunta_texto_aplicado: str | None = None
    exemplo_esperado_aplicado: str | None = None
    competencia_id_aplicada: int | None = None
    competencia_nome_aplicada: str | None = None
    peso_pergunta_aplicado: float | None = None
    usa_star_aplicado: bool | None = None
    ordem_pergunta_aplicada: int | None = None


# ============================================================
# AVALIAÇÃO
# ============================================================

@dataclass
class Avaliacao:
    """Guarda o resultado geral da avaliação de uma resposta."""

    id: int | None = None
    resposta_id: int | None = None
    pontuacao: float | None = None
    pontos_fortes: str | None = None
    pontos_melhoria: str | None = None
    feedback: str | None = None
    modelo_ia: str | None = None
    data_avaliacao: str | None = None


# ============================================================
# AVALIAÇÃO POR CRITÉRIO
# ============================================================

@dataclass
class AvaliacaoCriterio:
    """Guarda a nota de um critério e os dados históricos usados na avaliação."""

    id: int | None = None
    avaliacao_id: int | None = None
    criterio_id: int | None = None
    nota: float = 0.0
    observacao: str | None = None

    # Snapshot histórico do critério.
    peso_aplicado: float | None = None
    criterio_nome_aplicado: str | None = None
    criterio_descricao_aplicada: str | None = None
    criterio_ordem_aplicada: int | None = None


# ============================================================
# HISTÓRICO DE ACESSO
# ============================================================

@dataclass
class HistoricoAcesso:
    """Guarda uma ação realizada por um usuário no sistema."""

    id: int | None = None
    usuario_id: int | None = None
    acao: str = ""
    descricao: str | None = None
    data_acao: str | None = None
    ip: str | None = None


# ============================================================
# CONFIGURAÇÃO
# ============================================================

@dataclass
class Configuracao:
    """Guarda uma configuração geral e não sensível da aplicação."""

    id: int | None = None
    chave: str = ""
    valor: str | None = None
    descricao: str | None = None
    data_atualizacao: str | None = None
