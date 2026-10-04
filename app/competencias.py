"""
competencias.py

Módulo responsável pelo gerenciamento das competências
do Simulador de Entrevistas.

Versão: 0.3

Responsabilidades:

- cadastrar competências;
- listar competências;
- buscar competência por ID;
- editar competências;
- ativar competências;
- inativar competências;
- consultar quantidade de perguntas vinculadas;
- consultar quantidade de perguntas ativas vinculadas;
- verificar se uma competência está em uso;
- impedir a inativação de competências que possuam
  perguntas ativas.

IMPORTANTE:

Na tabela competencias, o campo utilizado para representar
o status é denominado:

    ativa

Na API, entretanto, o campo retornado é apresentado como:

    ativo

Essa diferença é tratada internamente neste módulo.
"""

import sqlite3


try:

    from .database import conectar_banco

except ImportError:

    from database import conectar_banco


# ============================================================
# CONFIGURAÇÕES
# ============================================================

TAMANHO_MAXIMO_NOME = 100

TAMANHO_MAXIMO_DESCRICAO = 1000


# ============================================================
# VALIDAR ID
# ============================================================

def _validar_id(
    competencia_id: int
) -> None:
    """
    Valida o ID de uma competência.
    """

    if not isinstance(
        competencia_id,
        int
    ):

        raise ValueError(
            "O ID da competência deve ser um número inteiro."
        )


    if competencia_id <= 0:

        raise ValueError(
            "O ID da competência deve ser maior que zero."
        )


# ============================================================
# NORMALIZAR NOME
# ============================================================

def _normalizar_nome(
    nome: str
) -> str:
    """
    Normaliza e valida o nome da competência.
    """

    if nome is None:

        raise ValueError(
            "O nome da competência é obrigatório."
        )


    if not isinstance(
        nome,
        str
    ):

        raise ValueError(
            "O nome da competência deve ser um texto."
        )


    nome = nome.strip()


    if not nome:

        raise ValueError(
            "O nome da competência não pode estar vazio."
        )


    if len(nome) > TAMANHO_MAXIMO_NOME:

        raise ValueError(
            "O nome da competência deve possuir no máximo "
            f"{TAMANHO_MAXIMO_NOME} caracteres."
        )


    return nome


# ============================================================
# NORMALIZAR DESCRIÇÃO
# ============================================================

def _normalizar_descricao(
    descricao: str | None
) -> str | None:
    """
    Normaliza a descrição da competência.
    """

    if descricao is None:

        return None


    if not isinstance(
        descricao,
        str
    ):

        raise ValueError(
            "A descrição da competência deve ser um texto."
        )


    descricao = descricao.strip()


    if not descricao:

        return None


    if len(descricao) > TAMANHO_MAXIMO_DESCRICAO:

        raise ValueError(
            "A descrição da competência deve possuir no máximo "
            f"{TAMANHO_MAXIMO_DESCRICAO} caracteres."
        )


    return descricao


# ============================================================
# CONVERTER REGISTRO PARA DICIONÁRIO
# ============================================================

def _registro_para_dict(
    registro: sqlite3.Row
) -> dict:
    """
    Converte um registro SQLite para o formato
    retornado pela API.

    Banco:
        ativa

    API:
        ativo
    """

    return {

        "id":
            registro["id"],

        "nome":
            registro["nome"],

        "descricao":
            registro["descricao"],

        "ativo":
            bool(
                registro["ativa"]
            )

    }


# ============================================================
# VERIFICAR NOME EXISTENTE
# ============================================================

def nome_competencia_existe(
    nome: str,
    ignorar_id: int | None = None
) -> bool:
    """
    Verifica se já existe uma competência
    com determinado nome.

    A comparação não diferencia maiúsculas
    de minúsculas.
    """

    nome = _normalizar_nome(
        nome
    )


    conexao = conectar_banco()

    cursor = conexao.cursor()


    try:

        if ignorar_id is None:

            cursor.execute(
                """
                SELECT id

                FROM competencias

                WHERE LOWER(nome) = LOWER(?)

                LIMIT 1
                """,
                (
                    nome,
                )
            )


        else:

            _validar_id(
                ignorar_id
            )


            cursor.execute(
                """
                SELECT id

                FROM competencias

                WHERE LOWER(nome) = LOWER(?)

                  AND id <> ?

                LIMIT 1
                """,
                (
                    nome,
                    ignorar_id
                )
            )


        return (
            cursor.fetchone()
            is not None
        )


    finally:

        conexao.close()


# ============================================================
# CADASTRAR COMPETÊNCIA
# ============================================================

def cadastrar_competencia(
    nome: str,
    descricao: str | None = None
) -> int:
    """
    Cadastra uma nova competência.

    A competência é criada inicialmente ativa.

    Retorna o ID gerado.
    """

    nome = _normalizar_nome(
        nome
    )


    descricao = _normalizar_descricao(
        descricao
    )


    if nome_competencia_existe(
        nome
    ):

        raise ValueError(
            "Já existe uma competência cadastrada "
            "com esse nome."
        )


    conexao = conectar_banco()

    cursor = conexao.cursor()


    try:

        cursor.execute(
            """
            INSERT INTO competencias (
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


        competencia_id = (
            cursor.lastrowid
        )


        conexao.commit()


        return competencia_id


    except sqlite3.IntegrityError:

        conexao.rollback()

        raise ValueError(
            "Já existe uma competência cadastrada "
            "com esse nome."
        )


    except sqlite3.Error:

        conexao.rollback()

        raise


    finally:

        conexao.close()


# ============================================================
# LISTAR COMPETÊNCIAS
# ============================================================

def listar_competencias(
    somente_ativas: bool = False
) -> list[dict]:
    """
    Lista as competências cadastradas.

    Quando somente_ativas=True,
    retorna somente competências ativas.
    """

    conexao = conectar_banco()

    cursor = conexao.cursor()


    try:

        if somente_ativas:

            cursor.execute(
                """
                SELECT
                    id,
                    nome,
                    descricao,
                    ativa

                FROM competencias

                WHERE ativa = 1

                ORDER BY
                    nome COLLATE NOCASE,
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
                    ativa

                FROM competencias

                ORDER BY
                    nome COLLATE NOCASE,
                    id
                """
            )


        registros = cursor.fetchall()


        return [

            _registro_para_dict(
                registro
            )

            for registro in registros
        ]


    finally:

        conexao.close()


# ============================================================
# BUSCAR COMPETÊNCIA
# ============================================================

def buscar_competencia(
    competencia_id: int
) -> dict | None:
    """
    Busca uma competência pelo ID.
    """

    _validar_id(
        competencia_id
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
                ativa

            FROM competencias

            WHERE id = ?
            """,
            (
                competencia_id,
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
# EDITAR COMPETÊNCIA
# ============================================================

def editar_competencia(
    competencia_id: int,
    nome: str,
    descricao: str | None = None
) -> bool:
    """
    Atualiza os dados de uma competência.

    Quando descricao=None, a descrição atual
    é preservada.
    """

    _validar_id(
        competencia_id
    )


    nome = _normalizar_nome(
        nome
    )


    competencia_atual = buscar_competencia(
        competencia_id
    )


    if competencia_atual is None:

        return False


    if nome_competencia_existe(
        nome,
        ignorar_id=competencia_id
    ):

        raise ValueError(
            "Já existe uma competência cadastrada "
            "com esse nome."
        )


    # --------------------------------------------------------
    # PRESERVAR DESCRIÇÃO QUANDO NÃO INFORMADA
    # --------------------------------------------------------

    if descricao is None:

        descricao_final = (
            competencia_atual[
                "descricao"
            ]
        )


    else:

        descricao_final = (
            _normalizar_descricao(
                descricao
            )
        )


    conexao = conectar_banco()

    cursor = conexao.cursor()


    try:

        cursor.execute(
            """
            UPDATE competencias

            SET
                nome = ?,
                descricao = ?

            WHERE id = ?
            """,
            (
                nome,
                descricao_final,
                competencia_id
            )
        )


        conexao.commit()


        return True


    except sqlite3.IntegrityError:

        conexao.rollback()

        raise ValueError(
            "Já existe uma competência cadastrada "
            "com esse nome."
        )


    except sqlite3.Error:

        conexao.rollback()

        raise


    finally:

        conexao.close()


# ============================================================
# CONTAR PERGUNTAS DA COMPETÊNCIA
# ============================================================

def contar_perguntas_competencia(
    competencia_id: int
) -> int:
    """
    Retorna a quantidade total de perguntas
    vinculadas à competência.

    Considera perguntas ativas e inativas.
    """

    _validar_id(
        competencia_id
    )


    conexao = conectar_banco()

    cursor = conexao.cursor()


    try:

        cursor.execute(
            """
            SELECT
                COUNT(*) AS quantidade

            FROM perguntas

            WHERE competencia_id = ?
            """,
            (
                competencia_id,
            )
        )


        registro = cursor.fetchone()


        return int(
            registro["quantidade"]
        )


    finally:

        conexao.close()


# ============================================================
# CONTAR PERGUNTAS ATIVAS DA COMPETÊNCIA
# ============================================================

def contar_perguntas_ativas_competencia(
    competencia_id: int
) -> int:
    """
    Retorna a quantidade de perguntas ativas
    vinculadas à competência.

    Esta função é utilizada pela regra de integridade
    que impede a inativação de uma competência enquanto
    existirem perguntas ativas relacionadas.
    """

    _validar_id(
        competencia_id
    )


    conexao = conectar_banco()

    cursor = conexao.cursor()


    try:

        cursor.execute(
            """
            SELECT
                COUNT(*) AS quantidade

            FROM perguntas

            WHERE competencia_id = ?

              AND ativa = 1
            """,
            (
                competencia_id,
            )
        )


        registro = cursor.fetchone()


        return int(
            registro["quantidade"]
        )


    finally:

        conexao.close()


# ============================================================
# VERIFICAR SE COMPETÊNCIA ESTÁ EM USO
# ============================================================

def competencia_em_uso(
    competencia_id: int
) -> bool:
    """
    Verifica se existem perguntas vinculadas
    à competência.

    Uma competência pode estar em uso mesmo que
    todas as perguntas estejam inativas.
    """

    return (
        contar_perguntas_competencia(
            competencia_id
        )
        > 0
    )


# ============================================================
# ATIVAR COMPETÊNCIA
# ============================================================

def ativar_competencia(
    competencia_id: int
) -> bool:
    """
    Ativa uma competência.
    """

    _validar_id(
        competencia_id
    )


    competencia = buscar_competencia(
        competencia_id
    )


    if competencia is None:

        return False


    if competencia["ativo"]:

        return True


    return _alterar_status_competencia(
        competencia_id,
        True
    )


# ============================================================
# INATIVAR COMPETÊNCIA
# ============================================================

def inativar_competencia(
    competencia_id: int
) -> bool:
    """
    Inativa uma competência.

    REGRA DE INTEGRIDADE:

    Uma competência NÃO pode ser inativada enquanto
    possuir perguntas ativas vinculadas.

    Isso evita que uma pergunta permaneça ativa
    apontando para uma competência inativa.

    Perguntas inativas não impedem a inativação
    da competência.
    """

    _validar_id(
        competencia_id
    )


    competencia = buscar_competencia(
        competencia_id
    )


    if competencia is None:

        return False


    # --------------------------------------------------------
    # JÁ ESTÁ INATIVA
    # --------------------------------------------------------

    if not competencia["ativo"]:

        return True


    # --------------------------------------------------------
    # VERIFICAR PERGUNTAS ATIVAS
    # --------------------------------------------------------

    quantidade_perguntas_ativas = (
        contar_perguntas_ativas_competencia(
            competencia_id
        )
    )


    if quantidade_perguntas_ativas > 0:

        raise ValueError(
            "A competência não pode ser inativada porque "
            "possui perguntas ativas vinculadas."
        )


    # --------------------------------------------------------
    # INATIVAR
    # --------------------------------------------------------

    return _alterar_status_competencia(
        competencia_id,
        False
    )


# ============================================================
# ALTERAR STATUS
# ============================================================

def _alterar_status_competencia(
    competencia_id: int,
    ativa: bool
) -> bool:
    """
    Altera o status da competência.
    """

    _validar_id(
        competencia_id
    )


    conexao = conectar_banco()

    cursor = conexao.cursor()


    try:

        cursor.execute(
            """
            UPDATE competencias

            SET ativa = ?

            WHERE id = ?
            """,
            (
                1
                if ativa
                else 0,

                competencia_id
            )
        )


        conexao.commit()


        return (
            cursor.rowcount > 0
        )


    except sqlite3.Error:

        conexao.rollback()

        raise


    finally:

        conexao.close()


# ============================================================
# DETALHES DA COMPETÊNCIA
# ============================================================

def obter_detalhes_competencia(
    competencia_id: int
) -> dict | None:
    """
    Retorna informações detalhadas da competência.

    Inclui:

    - dados da competência;
    - quantidade total de perguntas;
    - quantidade de perguntas ativas;
    - informação de uso.
    """

    _validar_id(
        competencia_id
    )


    competencia = buscar_competencia(
        competencia_id
    )


    if competencia is None:

        return None


    quantidade_perguntas = (
        contar_perguntas_competencia(
            competencia_id
        )
    )


    quantidade_perguntas_ativas = (
        contar_perguntas_ativas_competencia(
            competencia_id
        )
    )


    return {

        "id":
            competencia["id"],

        "nome":
            competencia["nome"],

        "descricao":
            competencia["descricao"],

        "ativo":
            competencia["ativo"],

        "quantidade_perguntas":
            quantidade_perguntas,

        "quantidade_perguntas_ativas":
            quantidade_perguntas_ativas,

        "em_uso":
            quantidade_perguntas > 0

    }