"""
models.py

Modelos de dados do Simulador de Entrevistas.

Versão: 0.2

Os modelos representam as principais entidades utilizadas
pela aplicação.

O acesso ao SQLite continua sendo realizado pelo módulo
database.py utilizando sqlite3.

IMPORTANTE:

As notas de clareza, objetividade, coerência,
argumentação e adequação não são mais campos fixos
da classe Avaliacao.

Cada nota será representada por AvaliacaoCriterio.

Isso permite adicionar ou remover critérios futuramente
sem alterar a estrutura da tabela de avaliações.
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

    Perfis inicialmente permitidos:

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
    """

    id: Optional[int] = None

    nome: str = ""

    descricao: Optional[str] = None

    ativo: bool = True

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

    Exemplos iniciais:

    - Clareza
    - Objetividade
    - Coerência
    - Argumentação
    - Adequação à pergunta

    O peso será utilizado posteriormente pelo
    Motor de Pontuação.
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
    """

    id: Optional[int] = None

    usuario_id: Optional[int] = None

    tipo_entrevista_id: Optional[int] = None

    data_inicio: Optional[str] = None

    data_fim: Optional[str] = None

    status: str = "em_andamento"

    pontuacao_final: Optional[float] = None

    observacoes: Optional[str] = None


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
    """

    id: Optional[int] = None

    entrevista_id: Optional[int] = None

    pergunta_id: Optional[int] = None

    texto_resposta: str = ""

    tempo_resposta: Optional[int] = None

    data_resposta: Optional[str] = None


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

    As notas individuais NÃO ficam nesta classe.

    Elas são armazenadas através da classe
    AvaliacaoCriterio.
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

    Exemplo:

    avaliacao_id = 10
    criterio_id = 1
    nota = 8.5

    O criterio_id = 1 poderá representar
    "Clareza".

    Dessa forma, novos critérios poderão ser
    adicionados sem alterar a tabela avaliacoes.
    """

    id: Optional[int] = None

    avaliacao_id: Optional[int] = None

    criterio_id: Optional[int] = None

    nota: float = 0.0

    observacao: Optional[str] = None


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

    Chaves, tokens e outras credenciais sensíveis
    não devem ser armazenados nesta entidade.
    """

    id: Optional[int] = None

    chave: str = ""

    valor: Optional[str] = None

    descricao: Optional[str] = None

    data_atualizacao: Optional[str] = None