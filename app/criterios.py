"""
criterios.py

Módulo responsável pelos critérios de avaliação
e pela inicialização dos dados básicos do
Simulador de Entrevistas.

Versão: 0.2

Responsabilidades administrativas:

- cadastrar critérios;
- listar critérios;
- consultar critérios;
- atualizar critérios;
- ativar critérios;
- inativar critérios;
- impedir nomes duplicados;
- preservar critérios utilizados em avaliações;
- apresentar resumo dos pesos ativos.

Responsabilidades de inicialização:

- cadastrar tipos de entrevista iniciais;
- cadastrar competências iniciais;
- cadastrar critérios de avaliação iniciais.

IMPORTANTE:

Os critérios de avaliação não são excluídos
fisicamente.

Quando um critério deixa de ser utilizado,
ele deve ser inativado.

Isso preserva as avaliações históricas que possuem
referência ao criterio_id.

Os pesos não precisam obrigatoriamente somar 1.0.

O Motor de Pontuação normaliza os pesos utilizando
a soma dos critérios ativos.

Entretanto, todos os critérios cadastrados por esta
API devem possuir peso maior que zero.
"""

import sqlite3

try:

    from .database import conectar_banco

except ImportError:

    from database import conectar_banco


# ============================================================
# CONSTANTES
# ============================================================

TAMANHO_MAXIMO_NOME = 150

TAMANHO_MAXIMO_DESCRICAO = 2000


# ============================================================
# TIPOS DE ENTREVISTA INICIAIS
# ============================================================

TIPOS_ENTREVISTA = [

    (
        "Comportamental",
        "Entrevista destinada à avaliação de experiências, "
        "comportamentos e competências profissionais."
    ),

    (
        "Técnica",
        "Entrevista destinada à avaliação de conhecimentos "
        "e competências técnicas relacionadas à área profissional."
    ),

    (
        "Liderança",
        "Entrevista destinada à avaliação de competências "
        "relacionadas à liderança, tomada de decisão, gestão "
        "de equipes e resolução de conflitos."
    )

]


# ============================================================
# COMPETÊNCIAS INICIAIS
# ============================================================

COMPETENCIAS = [

    (
        "Comunicação",
        "Capacidade de apresentar ideias e informações "
        "de maneira compreensível e organizada."
    ),

    (
        "Trabalho em equipe",
        "Capacidade de colaborar com outras pessoas "
        "para alcançar objetivos comuns."
    ),

    (
        "Resolução de problemas",
        "Capacidade de analisar situações, identificar "
        "problemas e desenvolver soluções adequadas."
    ),

    (
        "Liderança",
        "Capacidade de orientar pessoas, organizar atividades "
        "e contribuir para o alcance de objetivos coletivos."
    ),

    (
        "Adaptabilidade",
        "Capacidade de se adaptar a mudanças, novos contextos "
        "e diferentes situações profissionais."
    ),

    (
        "Pensamento crítico",
        "Capacidade de analisar informações e situações "
        "de maneira lógica e fundamentada."
    ),

    (
        "Organização",
        "Capacidade de planejar e organizar atividades, "
        "prioridades e responsabilidades."
    ),

    (
        "Tomada de decisão",
        "Capacidade de avaliar alternativas e escolher "
        "ações adequadas diante de diferentes situações."
    )

]


# ============================================================
# CRITÉRIOS DE AVALIAÇÃO INICIAIS
# ============================================================

CRITERIOS_AVALIACAO = [

    (
        "Clareza",

        "Avalia se a resposta é compreensível e se as ideias "
        "são apresentadas de maneira organizada.",

        0.20,

        1
    ),

    (
        "Objetividade",

        "Avalia se o estudante responde diretamente ao que "
        "foi solicitado, evitando informações desnecessárias.",

        0.15,

        2
    ),

    (
        "Coerência",

        "Avalia a relação lógica entre as ideias apresentadas "
        "e a consistência da resposta.",

        0.20,

        3
    ),

    (
        "Argumentação",

        "Avalia a capacidade de desenvolver, justificar "
        "e sustentar as informações apresentadas.",

        0.20,

        4
    ),

    (
        "Adequação à pergunta",

        "Avalia se a resposta apresentada atende efetivamente "
        "ao conteúdo solicitado pela pergunta.",

        0.25,

        5
    )

]


# ============================================================
# VALIDAR ID
# ============================================================

def _validar_id(
    criterio_id: int
) -> None:
    """
    Valida o ID do critério.
    """

    if not isinstance(
        criterio_id,
        int
    ):

        raise ValueError(
            "O ID do critério deve ser um número inteiro."
        )


    if criterio_id <= 0:

        raise ValueError(
            "O ID do critério deve ser maior que zero."
        )


# ============================================================
# NORMALIZAR NOME
# ============================================================

def _normalizar_nome(
    nome: str
) -> str:
    """
    Valida e normaliza o nome do critério.
    """

    if nome is None:

        raise ValueError(
            "O nome do critério é obrigatório."
        )


    if not isinstance(
        nome,
        str
    ):

        raise ValueError(
            "O nome do critério deve ser um texto."
        )


    nome_normalizado = nome.strip()


    if not nome_normalizado:

        raise ValueError(
            "O nome do critério não pode estar vazio."
        )


    if len(
        nome_normalizado
    ) > TAMANHO_MAXIMO_NOME:

        raise ValueError(
            "O nome do critério não pode possuir mais de "
            f"{TAMANHO_MAXIMO_NOME} caracteres."
        )


    return nome_normalizado


# ============================================================
# NORMALIZAR DESCRIÇÃO
# ============================================================

def _normalizar_descricao(
    descricao: str | None
) -> str | None:
    """
    Valida e normaliza a descrição.
    """

    if descricao is None:

        return None


    if not isinstance(
        descricao,
        str
    ):

        raise ValueError(
            "A descrição do critério deve ser um texto."
        )


    descricao_normalizada = descricao.strip()


    if not descricao_normalizada:

        return None


    if len(
        descricao_normalizada
    ) > TAMANHO_MAXIMO_DESCRICAO:

        raise ValueError(
            "A descrição não pode possuir mais de "
            f"{TAMANHO_MAXIMO_DESCRICAO} caracteres."
        )


    return descricao_normalizada


# ============================================================
# NORMALIZAR PESO
# ============================================================

def _normalizar_peso(
    peso: float
) -> float:
    """
    Valida o peso do critério.
    """

    try:

        peso_normalizado = float(
            peso
        )

    except (
        TypeError,
        ValueError
    ):

        raise ValueError(
            "O peso do critério deve ser numérico."
        )


    if peso_normalizado <= 0:

        raise ValueError(
            "O peso do critério deve ser maior que zero."
        )


    return peso_normalizado


# ============================================================
# NORMALIZAR ORDEM
# ============================================================

def _normalizar_ordem(
    ordem: int | None
) -> int | None:
    """
    Valida a ordem do critério.
    """

    if ordem is None:

        return None


    if not isinstance(
        ordem,
        int
    ):

        raise ValueError(
            "A ordem do critério deve ser um número inteiro."
        )


    if ordem <= 0:

        raise ValueError(
            "A ordem do critério deve ser maior que zero."
        )


    return ordem


# ============================================================
# CONVERTER REGISTRO
# ============================================================

def _registro_para_dict(
    registro: sqlite3.Row
) -> dict:
    """
    Converte um registro SQLite para dicionário.
    """

    return {

        "id":
            registro["id"],

        "nome":
            registro["nome"],

        "descricao":
            registro["descricao"],

        "peso":
            float(
                registro["peso"]
            ),

        "ordem":
            registro["ordem"],

        "ativo":
            bool(
                registro["ativo"]
            )
    }


# ============================================================
# VERIFICAR NOME DUPLICADO
# ============================================================

def nome_criterio_existe(
    nome: str,
    ignorar_id: int | None = None
) -> bool:
    """
    Verifica se já existe critério com o mesmo nome.

    A comparação ignora maiúsculas/minúsculas.
    """

    nome_normalizado = _normalizar_nome(
        nome
    )


    conexao = conectar_banco()

    cursor = conexao.cursor()


    try:

        if ignorar_id is not None:

            _validar_id(
                ignorar_id
            )


            cursor.execute(
                """
                SELECT id

                FROM criterios_avaliacao

                WHERE LOWER(TRIM(nome))
                      = LOWER(TRIM(?))

                  AND id <> ?

                LIMIT 1
                """,
                (
                    nome_normalizado,
                    ignorar_id
                )
            )


        else:

            cursor.execute(
                """
                SELECT id

                FROM criterios_avaliacao

                WHERE LOWER(TRIM(nome))
                      = LOWER(TRIM(?))

                LIMIT 1
                """,
                (
                    nome_normalizado,
                )
            )


        return cursor.fetchone() is not None


    finally:

        conexao.close()


# ============================================================
# OBTER PRÓXIMA ORDEM
# ============================================================

def obter_proxima_ordem() -> int:
    """
    Retorna a próxima ordem disponível.
    """

    conexao = conectar_banco()

    cursor = conexao.cursor()


    try:

        cursor.execute(
            """
            SELECT
                COALESCE(
                    MAX(ordem),
                    0
                ) + 1 AS proxima_ordem

            FROM criterios_avaliacao
            """
        )


        registro = cursor.fetchone()


        return int(
            registro["proxima_ordem"]
        )


    finally:

        conexao.close()


# ============================================================
# CADASTRAR CRITÉRIO
# ============================================================

def cadastrar_criterio(
    nome: str,
    descricao: str | None,
    peso: float,
    ordem: int | None = None
) -> int:
    """
    Cadastra um novo critério de avaliação.

    O critério é criado ativo.
    """

    nome_normalizado = _normalizar_nome(
        nome
    )


    descricao_normalizada = (
        _normalizar_descricao(
            descricao
        )
    )


    peso_normalizado = _normalizar_peso(
        peso
    )


    ordem_normalizada = _normalizar_ordem(
        ordem
    )


    if nome_criterio_existe(
        nome_normalizado
    ):

        raise ValueError(
            "Já existe um critério de avaliação "
            "cadastrado com esse nome."
        )


    if ordem_normalizada is None:

        ordem_normalizada = (
            obter_proxima_ordem()
        )


    conexao = conectar_banco()

    cursor = conexao.cursor()


    try:

        cursor.execute(
            """
            INSERT INTO criterios_avaliacao (
                nome,
                descricao,
                peso,
                ordem,
                ativo
            )

            VALUES (?, ?, ?, ?, 1)
            """,
            (
                nome_normalizado,
                descricao_normalizada,
                peso_normalizado,
                ordem_normalizada
            )
        )


        criterio_id = (
            cursor.lastrowid
        )


        conexao.commit()


        return criterio_id


    except sqlite3.IntegrityError as erro:

        conexao.rollback()


        raise ValueError(
            "Não foi possível cadastrar o critério."
        ) from erro


    except sqlite3.Error:

        conexao.rollback()

        raise


    finally:

        conexao.close()


# ============================================================
# LISTAR CRITÉRIOS
# ============================================================

def listar_criterios(
    somente_ativos: bool = False
) -> list[dict]:
    """
    Lista os critérios cadastrados.
    """

    conexao = conectar_banco()

    cursor = conexao.cursor()


    try:

        if somente_ativos:

            cursor.execute(
                """
                SELECT
                    id,
                    nome,
                    descricao,
                    peso,
                    ordem,
                    ativo

                FROM criterios_avaliacao

                WHERE ativo = 1

                ORDER BY
                    COALESCE(ordem, 999999),
                    id
                """
            )


        else:

            cursor.execute(
                """
                SELECT
                    id,
                    nome,
                    descricao,
                    peso,
                    ordem,
                    ativo

                FROM criterios_avaliacao

                ORDER BY
                    COALESCE(ordem, 999999),
                    id
                """
            )


        return [

            _registro_para_dict(
                registro
            )

            for registro in cursor.fetchall()
        ]


    finally:

        conexao.close()


# ============================================================
# BUSCAR CRITÉRIO
# ============================================================

def buscar_criterio(
    criterio_id: int
) -> dict | None:
    """
    Busca um critério pelo ID.
    """

    _validar_id(
        criterio_id
    )


    conexao = conectar_banco()

    cursor = conexao.cursor()


    try:

        cursor.execute(
            """
            SELECT
                id,
                nome,
                descricao,
                peso,
                ordem,
                ativo

            FROM criterios_avaliacao

            WHERE id = ?
            """,
            (
                criterio_id,
            )
        )


        registro = cursor.fetchone()


        if registro is None:

            return None


        return _registro_para_dict(
            registro
        )


    finally:

        conexao.close()


# ============================================================
# EDITAR CRITÉRIO
# ============================================================

def editar_criterio(
    criterio_id: int,
    nome: str,
    descricao: str | None,
    peso: float,
    ordem: int | None = None
) -> bool:
    """
    Atualiza um critério existente.

    O status ativo/inativo não é alterado.
    """

    _validar_id(
        criterio_id
    )


    criterio_atual = buscar_criterio(
        criterio_id
    )


    if criterio_atual is None:

        return False


    nome_normalizado = _normalizar_nome(
        nome
    )


    descricao_normalizada = (
        _normalizar_descricao(
            descricao
        )
    )


    peso_normalizado = _normalizar_peso(
        peso
    )


    if ordem is None:

        ordem_normalizada = (
            criterio_atual["ordem"]
        )

    else:

        ordem_normalizada = (
            _normalizar_ordem(
                ordem
            )
        )


    if nome_criterio_existe(
        nome_normalizado,
        ignorar_id=criterio_id
    ):

        raise ValueError(
            "Já existe outro critério cadastrado "
            "com esse nome."
        )


    conexao = conectar_banco()

    cursor = conexao.cursor()


    try:

        cursor.execute(
            """
            UPDATE criterios_avaliacao

            SET
                nome = ?,
                descricao = ?,
                peso = ?,
                ordem = ?

            WHERE id = ?
            """,
            (
                nome_normalizado,
                descricao_normalizada,
                peso_normalizado,
                ordem_normalizada,
                criterio_id
            )
        )


        conexao.commit()


        return cursor.rowcount > 0


    except sqlite3.IntegrityError as erro:

        conexao.rollback()


        raise ValueError(
            "Não foi possível atualizar o critério."
        ) from erro


    except sqlite3.Error:

        conexao.rollback()

        raise


    finally:

        conexao.close()


# ============================================================
# CONTAR CRITÉRIOS ATIVOS
# ============================================================

def contar_criterios_ativos() -> int:
    """
    Retorna a quantidade de critérios ativos.
    """

    conexao = conectar_banco()

    cursor = conexao.cursor()


    try:

        cursor.execute(
            """
            SELECT COUNT(*) AS quantidade

            FROM criterios_avaliacao

            WHERE ativo = 1
            """
        )


        registro = cursor.fetchone()


        return int(
            registro["quantidade"]
        )


    finally:

        conexao.close()


# ============================================================
# ATIVAR CRITÉRIO
# ============================================================

def ativar_criterio(
    criterio_id: int
) -> bool:
    """
    Ativa um critério.
    """

    return _alterar_status_criterio(
        criterio_id,
        True
    )


# ============================================================
# INATIVAR CRITÉRIO
# ============================================================

def inativar_criterio(
    criterio_id: int
) -> bool:
    """
    Inativa um critério.

    Não permite que o sistema fique sem
    nenhum critério ativo.
    """

    _validar_id(
        criterio_id
    )


    criterio = buscar_criterio(
        criterio_id
    )


    if criterio is None:

        return False


    if not criterio["ativo"]:

        return True


    quantidade_ativos = (
        contar_criterios_ativos()
    )


    if quantidade_ativos <= 1:

        raise ValueError(
            "Não é possível inativar o último "
            "critério ativo do sistema."
        )


    return _alterar_status_criterio(
        criterio_id,
        False
    )


# ============================================================
# ALTERAR STATUS
# ============================================================

def _alterar_status_criterio(
    criterio_id: int,
    ativo: bool
) -> bool:
    """
    Altera o status do critério.
    """

    _validar_id(
        criterio_id
    )


    conexao = conectar_banco()

    cursor = conexao.cursor()


    try:

        cursor.execute(
            """
            SELECT id

            FROM criterios_avaliacao

            WHERE id = ?
            """,
            (
                criterio_id,
            )
        )


        if cursor.fetchone() is None:

            return False


        cursor.execute(
            """
            UPDATE criterios_avaliacao

            SET ativo = ?

            WHERE id = ?
            """,
            (
                1 if ativo else 0,
                criterio_id
            )
        )


        conexao.commit()


        return True


    except sqlite3.Error:

        conexao.rollback()

        raise


    finally:

        conexao.close()


# ============================================================
# CONTAR AVALIAÇÕES VINCULADAS
# ============================================================

def contar_avaliacoes_criterio(
    criterio_id: int
) -> int:
    """
    Retorna quantas notas de avaliação utilizam
    o critério.
    """

    _validar_id(
        criterio_id
    )


    conexao = conectar_banco()

    cursor = conexao.cursor()


    try:

        cursor.execute(
            """
            SELECT COUNT(*) AS quantidade

            FROM avaliacao_criterios

            WHERE criterio_id = ?
            """,
            (
                criterio_id,
            )
        )


        registro = cursor.fetchone()


        return int(
            registro["quantidade"]
        )


    finally:

        conexao.close()


# ============================================================
# CRITÉRIO EM USO
# ============================================================

def criterio_em_uso(
    criterio_id: int
) -> bool:
    """
    Informa se o critério já foi utilizado
    em alguma avaliação.
    """

    return (
        contar_avaliacoes_criterio(
            criterio_id
        ) > 0
    )


# ============================================================
# DETALHES DO CRITÉRIO
# ============================================================

def obter_detalhes_criterio(
    criterio_id: int
) -> dict | None:
    """
    Retorna o critério e informações
    administrativas.
    """

    criterio = buscar_criterio(
        criterio_id
    )


    if criterio is None:

        return None


    quantidade_avaliacoes = (
        contar_avaliacoes_criterio(
            criterio_id
        )
    )


    return {

        **criterio,

        "quantidade_avaliacoes":
            quantidade_avaliacoes,

        "em_uso":
            quantidade_avaliacoes > 0
    }


# ============================================================
# RESUMO DOS PESOS
# ============================================================

def obter_resumo_pesos() -> dict:
    """
    Retorna informações sobre os pesos
    dos critérios ativos.

    Como o Motor de Pontuação normaliza os pesos,
    também é apresentada a participação percentual
    de cada critério sobre o total.
    """

    criterios = listar_criterios(
        somente_ativos=True
    )


    soma_pesos = sum(
        criterio["peso"]
        for criterio in criterios
    )


    distribuicao = []


    for criterio in criterios:

        if soma_pesos > 0:

            participacao = (
                criterio["peso"]
                / soma_pesos
            ) * 100

        else:

            participacao = 0.0


        distribuicao.append(
            {
                "criterio_id":
                    criterio["id"],

                "criterio":
                    criterio["nome"],

                "peso":
                    criterio["peso"],

                "participacao_percentual":
                    round(
                        participacao,
                        2
                    )
            }
        )


    return {

        "quantidade_criterios_ativos":
            len(
                criterios
            ),

        "soma_pesos_ativos":
            round(
                soma_pesos,
                6
            ),

        "sistema_pronto_para_avaliar":
            (
                len(criterios) > 0
                and soma_pesos > 0
            ),

        "pesos_somam_um":
            abs(
                soma_pesos - 1.0
            ) < 0.000001,

        "distribuicao":
            distribuicao
    }


# ============================================================
# CADASTRAR TIPOS DE ENTREVISTA INICIAIS
# ============================================================

def cadastrar_tipos_entrevista(
    cursor
):
    """
    Cadastra os tipos de entrevista iniciais.
    """

    for nome, descricao in TIPOS_ENTREVISTA:

        cursor.execute(
            """
            INSERT OR IGNORE INTO tipos_entrevista (
                nome,
                descricao,
                ativo
            )

            VALUES (?, ?, 1)
            """,
            (
                nome,
                descricao
            )
        )


# ============================================================
# CADASTRAR COMPETÊNCIAS INICIAIS
# ============================================================

def cadastrar_competencias(
    cursor
):
    """
    Cadastra as competências iniciais.
    """

    for nome, descricao in COMPETENCIAS:

        cursor.execute(
            """
            INSERT OR IGNORE INTO competencias (
                nome,
                descricao,
                ativa
            )

            VALUES (?, ?, 1)
            """,
            (
                nome,
                descricao
            )
        )


# ============================================================
# CADASTRAR CRITÉRIOS INICIAIS
# ============================================================

def cadastrar_criterios(
    cursor
):
    """
    Cadastra os critérios iniciais utilizados
    pela IA e pelo Motor de Pontuação.
    """

    for (
        nome,
        descricao,
        peso,
        ordem
    ) in CRITERIOS_AVALIACAO:

        cursor.execute(
            """
            INSERT OR IGNORE INTO criterios_avaliacao (
                nome,
                descricao,
                peso,
                ordem,
                ativo
            )

            VALUES (?, ?, ?, ?, 1)
            """,
            (
                nome,
                descricao,
                peso,
                ordem
            )
        )


# ============================================================
# MOSTRAR DADOS
# ============================================================

def mostrar_dados(
    cursor
):
    """
    Exibe os dados básicos após inicialização.
    """

    print()
    print(
        "=========================================="
    )
    print(
        "TIPOS DE ENTREVISTA"
    )
    print(
        "=========================================="
    )


    cursor.execute(
        """
        SELECT
            id,
            nome

        FROM tipos_entrevista

        ORDER BY id
        """
    )


    for registro in cursor.fetchall():

        print(
            f"{registro['id']} - "
            f"{registro['nome']}"
        )


    print()
    print(
        "=========================================="
    )
    print(
        "COMPETÊNCIAS"
    )
    print(
        "=========================================="
    )


    cursor.execute(
        """
        SELECT
            id,
            nome

        FROM competencias

        ORDER BY id
        """
    )


    for registro in cursor.fetchall():

        print(
            f"{registro['id']} - "
            f"{registro['nome']}"
        )


    print()
    print(
        "=========================================="
    )
    print(
        "CRITÉRIOS DE AVALIAÇÃO"
    )
    print(
        "=========================================="
    )


    cursor.execute(
        """
        SELECT
            id,
            nome,
            peso

        FROM criterios_avaliacao

        ORDER BY
            COALESCE(ordem, 999999),
            id
        """
    )


    for registro in cursor.fetchall():

        percentual = (
            registro["peso"]
            * 100
        )


        print(
            f"{registro['id']} - "
            f"{registro['nome']} "
            f"({percentual:.0f}%)"
        )


# ============================================================
# INICIALIZAR DADOS
# ============================================================

def inicializar_criterios():
    """
    Inicializa os dados básicos do sistema.
    """

    conexao = conectar_banco()

    cursor = conexao.cursor()


    try:

        cadastrar_tipos_entrevista(
            cursor
        )


        cadastrar_competencias(
            cursor
        )


        cadastrar_criterios(
            cursor
        )


        conexao.commit()


        print()
        print(
            "Dados iniciais cadastrados com sucesso."
        )


        mostrar_dados(
            cursor
        )


    except sqlite3.Error as erro:

        conexao.rollback()


        print(
            f"Erro ao cadastrar os dados iniciais: {erro}"
        )


        raise


    finally:

        conexao.close()


# ============================================================
# EXECUÇÃO DIRETA
# ============================================================

if __name__ == "__main__":

    inicializar_criterios()