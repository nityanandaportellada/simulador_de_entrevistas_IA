"""
models.py

Modelos de dados do Simulador de Entrevistas.

Versão: 0.6

Os modelos representam as principais entidades utilizadas
pela aplicação.

O acesso ao SQLite continua sendo realizado pelo módulo
database.py utilizando sqlite3.

Nesta versão também são representados:

- áreas técnicas;
- subáreas técnicas;
- seleção de área/subárea em perguntas técnicas;
- seleção de área/subárea em entrevistas técnicas;
- snapshots históricos;
- conjunto de perguntas congelado por entrevista.
"""

from dataclasses import dataclass

from typing import Optional


# ============================================================
# USUÁRIO
# ============================================================

@dataclass
class Usuario:
    """
    Representa um usuário do sistema.

    Perfis permitidos:

    - estudante
    - administrador
    """

    id: Optional[int] = None

    nome: str = ""

    email: str = ""

    senha_hash: str = ""

    perfil: str = "estudante"

    ativo: bool = True

    data_criacao: Optional[str] = None

    ultimo_acesso: Optional[str] = None


# ============================================================
# TIPO DE ENTREVISTA
# ============================================================

@dataclass
class TipoEntrevista:
    """
    Representa um tipo de entrevista.

    Exemplos:

    - Comportamental
    - Técnica
    - Liderança

    O campo usa_area_tecnica determina se o tipo
    exige seleção de área e subárea.
    """

    id: Optional[int] = None

    nome: str = ""

    descricao: Optional[str] = None

    ativo: bool = True

    data_criacao: Optional[str] = None

    usa_area_tecnica: bool = False


# ============================================================
# ÁREA TÉCNICA
# ============================================================

@dataclass
class AreaTecnica:
    """
    Representa uma área disponível para entrevistas técnicas.

    Áreas iniciais:

    - Direito
    - Psicologia
    - Administração
    - Economia
    - Ciências Contábeis
    - Tecnologia
    """

    id: Optional[int] = None

    nome: str = ""

    descricao: Optional[str] = None

    ativo: bool = True

    ordem: Optional[int] = None

    data_criacao: Optional[str] = None


# ============================================================
# SUBÁREA TÉCNICA
# ============================================================

@dataclass
class SubareaTecnica:
    """
    Representa uma subárea vinculada a uma área técnica.

    Toda área possui obrigatoriamente uma subárea
    protegida chamada Geral.
    """

    id: Optional[int] = None

    area_tecnica_id: Optional[int] = None

    nome: str = ""

    descricao: Optional[str] = None

    eh_geral: bool = False

    ativo: bool = True

    ordem: Optional[int] = None

    data_criacao: Optional[str] = None


# ============================================================
# COMPETÊNCIA
# ============================================================

@dataclass
class Competencia:
    """
    Representa uma competência profissional
    associada às perguntas.

    Exemplos:

    - Comunicação
    - Trabalho em equipe
    - Liderança
    - Resolução de problemas
    """

    id: Optional[int] = None

    nome: str = ""

    descricao: Optional[str] = None

    ativa: bool = True


# ============================================================
# CRITÉRIO DE AVALIAÇÃO
# ============================================================

@dataclass
class CriterioAvaliacao:
    """
    Representa um critério utilizado na análise
    das respostas.

    Exemplos:

    - Clareza
    - Objetividade
    - Coerência
    - Argumentação
    - Adequação à pergunta
    """

    id: Optional[int] = None

    nome: str = ""

    descricao: Optional[str] = None

    peso: float = 1.0

    ordem: Optional[int] = None

    ativo: bool = True


# ============================================================
# PERGUNTA
# ============================================================

@dataclass
class Pergunta:
    """
    Representa uma pergunta cadastrada no sistema.

    Cada pergunta possui:

    - tipo de entrevista;
    - competência;
    - texto;
    - peso;
    - indicação de utilização do método STAR.

    Perguntas pertencentes a tipos que utilizam
    área técnica também poderão possuir:

    - área técnica;
    - subárea técnica.
    """

    id: Optional[int] = None

    tipo_entrevista_id: Optional[int] = None

    competencia_id: Optional[int] = None

    texto: str = ""

    exemplo_esperado: Optional[str] = None

    ordem: Optional[int] = None

    ativa: bool = True

    peso: float = 1.0

    usa_star: bool = False

    data_criacao: Optional[str] = None

    area_tecnica_id: Optional[int] = None

    subarea_tecnica_id: Optional[int] = None


# ============================================================
# ENTREVISTA
# ============================================================

@dataclass
class Entrevista:
    """
    Representa uma entrevista realizada pelo estudante.

    Status possíveis:

    - em_andamento
    - finalizada
    - em_analise
    - avaliada
    - erro_analise
    - cancelada

    Os campos terminados em "_aplicado" preservam
    informações históricas.

    Dessa forma, alterações administrativas futuras
    não modificam entrevistas já realizadas.
    """

    id: Optional[int] = None

    usuario_id: Optional[int] = None

    tipo_entrevista_id: Optional[int] = None

    data_inicio: Optional[str] = None

    data_fim: Optional[str] = None

    status: str = "em_andamento"

    pontuacao_final: Optional[float] = None

    observacoes: Optional[str] = None


    # --------------------------------------------------------
    # SNAPSHOT DO TIPO DE ENTREVISTA
    # --------------------------------------------------------

    tipo_entrevista_nome_aplicado: Optional[str] = None

    tipo_entrevista_descricao_aplicada: Optional[str] = None


    # --------------------------------------------------------
    # ÁREA E SUBÁREA TÉCNICA
    # --------------------------------------------------------

    area_tecnica_id: Optional[int] = None

    subarea_tecnica_id: Optional[int] = None


    # --------------------------------------------------------
    # SNAPSHOT DA ÁREA E SUBÁREA
    # --------------------------------------------------------

    area_tecnica_nome_aplicado: Optional[str] = None

    subarea_tecnica_nome_aplicado: Optional[str] = None


# ============================================================
# PERGUNTA APLICADA À ENTREVISTA
# ============================================================

@dataclass
class EntrevistaPergunta:
    """
    Representa uma pergunta congelada no momento em
    que a entrevista é iniciada.

    Essa entidade será utilizada para impedir que uma
    alteração administrativa em uma pergunta modifique
    uma entrevista que já começou.

    Exemplo:

    uma entrevista técnica é iniciada com:

    área:
        Tecnologia

    subárea:
        Segurança da Informação

    As perguntas escolhidas naquele momento serão
    copiadas para entrevista_perguntas.

    Posteriormente, mesmo que o administrador edite
    a pergunta original, a entrevista continuará
    utilizando o snapshot.
    """

    id: Optional[int] = None

    entrevista_id: Optional[int] = None

    pergunta_id: Optional[int] = None


    # --------------------------------------------------------
    # SNAPSHOT DA PERGUNTA
    # --------------------------------------------------------

    pergunta_texto_aplicado: str = ""

    exemplo_esperado_aplicado: Optional[str] = None


    # --------------------------------------------------------
    # SNAPSHOT DA COMPETÊNCIA
    # --------------------------------------------------------

    competencia_id_aplicada: Optional[int] = None

    competencia_nome_aplicada: str = ""


    # --------------------------------------------------------
    # SNAPSHOT DA ÁREA
    # --------------------------------------------------------

    area_tecnica_id_aplicada: Optional[int] = None

    area_tecnica_nome_aplicada: Optional[str] = None


    # --------------------------------------------------------
    # SNAPSHOT DA SUBÁREA
    # --------------------------------------------------------

    subarea_tecnica_id_aplicada: Optional[int] = None

    subarea_tecnica_nome_aplicada: Optional[str] = None


    # --------------------------------------------------------
    # CONFIGURAÇÕES HISTÓRICAS DA PERGUNTA
    # --------------------------------------------------------

    peso_pergunta_aplicado: float = 1.0

    usa_star_aplicado: bool = False

    ordem_pergunta_aplicada: Optional[int] = None


    # --------------------------------------------------------
    # DATA
    # --------------------------------------------------------

    data_aplicacao: Optional[str] = None


# ============================================================
# RESPOSTA
# ============================================================

@dataclass
class Resposta:
    """
    Representa uma resposta fornecida pelo estudante.

    Cada resposta pertence a:

    - uma entrevista;
    - uma pergunta.

    A resposta também mantém o snapshot histórico
    da pergunta utilizada no momento da resposta.
    """

    id: Optional[int] = None

    entrevista_id: Optional[int] = None

    pergunta_id: Optional[int] = None

    texto_resposta: str = ""

    tempo_resposta: Optional[int] = None

    data_resposta: Optional[str] = None


    # --------------------------------------------------------
    # SNAPSHOT HISTÓRICO DA PERGUNTA
    # --------------------------------------------------------

    pergunta_texto_aplicado: Optional[str] = None

    exemplo_esperado_aplicado: Optional[str] = None

    competencia_id_aplicada: Optional[int] = None

    competencia_nome_aplicada: Optional[str] = None

    peso_pergunta_aplicado: Optional[float] = None

    usa_star_aplicado: Optional[bool] = None

    ordem_pergunta_aplicada: Optional[int] = None


# ============================================================
# AVALIAÇÃO
# ============================================================

@dataclass
class Avaliacao:
    """
    Representa a avaliação geral de uma resposta.

    A avaliação contém:

    - pontuação consolidada;
    - pontos fortes;
    - pontos de melhoria;
    - feedback;
    - identificação do modelo de IA.

    As notas individuais não ficam diretamente
    nesta classe.

    Elas são armazenadas por AvaliacaoCriterio.
    """

    id: Optional[int] = None

    resposta_id: Optional[int] = None

    pontuacao: Optional[float] = None

    pontos_fortes: Optional[str] = None

    pontos_melhoria: Optional[str] = None

    feedback: Optional[str] = None

    modelo_ia: Optional[str] = None

    data_avaliacao: Optional[str] = None


# ============================================================
# AVALIAÇÃO POR CRITÉRIO
# ============================================================

@dataclass
class AvaliacaoCriterio:
    """
    Representa a nota atribuída a um critério
    dentro de uma avaliação.

    Os campos de snapshot preservam o critério
    exatamente como ele existia no momento
    da avaliação.
    """

    id: Optional[int] = None

    avaliacao_id: Optional[int] = None

    criterio_id: Optional[int] = None

    nota: float = 0.0

    observacao: Optional[str] = None


    # --------------------------------------------------------
    # SNAPSHOT HISTÓRICO DO CRITÉRIO
    # --------------------------------------------------------

    peso_aplicado: Optional[float] = None

    criterio_nome_aplicado: Optional[str] = None

    criterio_descricao_aplicada: Optional[str] = None

    criterio_ordem_aplicada: Optional[int] = None


# ============================================================
# HISTÓRICO DE ACESSO
# ============================================================

@dataclass
class HistoricoAcesso:
    """
    Representa uma ação realizada pelo usuário.

    Exemplos:

    - login
    - logout
    - início de entrevista
    - finalização de entrevista
    - alteração administrativa
    """

    id: Optional[int] = None

    usuario_id: Optional[int] = None

    acao: str = ""

    descricao: Optional[str] = None

    data_acao: Optional[str] = None

    ip: Optional[str] = None


# ============================================================
# CONFIGURAÇÃO
# ============================================================

@dataclass
class Configuracao:
    """
    Representa uma configuração geral da aplicação.

    Exemplos:

    - quantidade padrão de perguntas;
    - parâmetros de avaliação;
    - outras configurações do sistema.

    Chaves, tokens e credenciais sensíveis
    não devem ser armazenados nesta entidade.
    """

    id: Optional[int] = None

    chave: str = ""

    valor: Optional[str] = None

    descricao: Optional[str] = None

    data_atualizacao: Optional[str] = None