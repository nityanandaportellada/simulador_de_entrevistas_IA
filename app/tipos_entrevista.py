"""
tipos_entrevista.py

Módulo responsável pelo gerenciamento dos tipos
de entrevista do Simulador de Entrevistas.

Versão: 0.2

Responsabilidades:

- cadastrar tipos de entrevista;
- listar tipos de entrevista;
- buscar tipo por ID;
- editar tipos;
- ativar tipos;
- inativar tipos;
- contar perguntas vinculadas;
- contar perguntas ativas vinculadas;
- contar entrevistas vinculadas;
- verificar utilização;
- impedir a inativação de um tipo enquanto
  existirem perguntas ativas relacionadas.

REGRA DE INTEGRIDADE:

Um tipo de entrevista não pode ser inativado
enquanto possuir perguntas ativas vinculadas.

Entrevistas históricas não impedem a inativação.

Isso permite preservar o histórico sem permitir
que novas entrevistas utilizem estruturas
administrativamente inativas.
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


# ============================================================
# VALIDAR ID
# ============================================================

def _validar_id(
    tipo_entrevista_id: int
) -> None:
    """
    Valida o ID de um tipo de entrevista.
    """

    if not isinstance(
        tipo_entrevista_id,
        int
    ):

        raise ValueError(
            "O ID do tipo de entrevista deve ser "
            "um número inteiro."
        )


    if tipo_entrevista_id <= 0:

        raise ValueError(
            "O ID do tipo de entrevista deve ser "
            "maior que zero."
        )


# ============================================================
# NORMALIZAR NOME
# ============================================================

def _normalizar_nome(
    nome: str
) -> str:
    """
    Normaliza e valida o nome de um tipo
    de entrevista.
    """

    if nome is None:

        raise ValueError(
            "O nome do tipo de entrevista é obrigatório."
        )


    if not isinstance(
        nome,
        str
    ):

        raise ValueError(
            "O nome do tipo de entrevista deve ser um texto."
        )


    nome = nome.strip()


    if not nome:

        raise ValueError(
            "O nome do tipo de entrevista não pode estar vazio."
        )


    if len(nome) > TAMANHO_MAXIMO_NOME:

        raise ValueError(
            "O nome do tipo de entrevista deve possuir "
            f"no máximo {TAMANHO_MAXIMO_NOME} caracteres."
        )


    return nome


# ============================================================
# CONVERTER REGISTRO
# ============================================================

def _registro_para_dict(
    registro: sqlite3.Row
) -> dict:
    """
    Converte um registro SQLite para
    o formato utilizado pela API.
    """

    return {

        "id":
            registro["id"],

        "nome":
            registro["nome"],

        "ativo":
            bool(
                registro["ativo"]
            )

    }


# ============================================================
# VERIFICAR NOME EXISTENTE
# ============================================================

def nome_tipo_entrevista_existe(
    nome: str,
    ignorar_id: int | None = None
) -> bool:
    """
    Verifica se já existe um tipo de entrevista
    com o mesmo nome.

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

                FROM tipos_entrevista

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

                FROM tipos_entrevista

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
# CADASTRAR TIPO
# ============================================================

def cadastrar_tipo_entrevista(
    nome: str
) -> int:
    """
    Cadastra um novo tipo de entrevista.

    O tipo é criado inicialmente ativo.

    Retorna o ID gerado.
    """

    nome = _normalizar_nome(
        nome
    )


    if nome_tipo_entrevista_existe(
        nome
    ):

        raise ValueError(
            "Já existe um tipo de entrevista "
            "cadastrado com esse nome."
        )


    conexao = conectar_banco()

    cursor = conexao.cursor()


    try:

        cursor.execute(
            """
            INSERT INTO tipos_entrevista (
                nome,
                ativo
            )

            VALUES (?, 1)
            """,
            (
                nome,
            )
        )


        tipo_entrevista_id = (
            cursor.lastrowid
        )


        conexao.commit()


        return tipo_entrevista_id


    except sqlite3.IntegrityError:

        conexao.rollback()

        raise ValueError(
            "Já existe um tipo de entrevista "
            "cadastrado com esse nome."
        )


    except sqlite3.Error:

        conexao.rollback()

        raise


    finally:

        conexao.close()


# ============================================================
# LISTAR TIPOS
# ============================================================

def listar_tipos_entrevista(
    somente_ativos: bool = False
) -> list[dict]:
    """
    Lista os tipos de entrevista cadastrados.

    Quando somente_ativos=True,
    retorna apenas tipos ativos.
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
                    ativo

                FROM tipos_entrevista

                WHERE ativo = 1

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
                    ativo

                FROM tipos_entrevista

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
# BUSCAR TIPO
# ============================================================

def buscar_tipo_entrevista(
    tipo_entrevista_id: int
) -> dict | None:
    """
    Busca um tipo de entrevista pelo ID.
    """

    _validar_id(
        tipo_entrevista_id
    )


    conexao = conectar_banco()

    cursor = conexao.cursor()


    try:

        cursor.execute(
            """
            SELECT
                id,
                nome,
                ativo

            FROM tipos_entrevista

            WHERE id = ?
            """,
            (
                tipo_entrevista_id,
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
# EDITAR TIPO
# ============================================================

def editar_tipo_entrevista(
    tipo_entrevista_id: int,
    nome: str
) -> bool:
    """
    Atualiza o nome de um tipo de entrevista.
    """

    _validar_id(
        tipo_entrevista_id
    )


    nome = _normalizar_nome(
        nome
    )


    tipo_atual = buscar_tipo_entrevista(
        tipo_entrevista_id
    )


    if tipo_atual is None:

        return False


    if nome_tipo_entrevista_existe(
        nome,
        ignorar_id=tipo_entrevista_id
    ):

        raise ValueError(
            "Já existe um tipo de entrevista "
            "cadastrado com esse nome."
        )


    conexao = conectar_banco()

    cursor = conexao.cursor()


    try:

        cursor.execute(
            """
            UPDATE tipos_entrevista

            SET nome = ?

            WHERE id = ?
            """,
            (
                nome,
                tipo_entrevista_id
            )
        )


        conexao.commit()


        return True


    except sqlite3.IntegrityError:

        conexao.rollback()

        raise ValueError(
            "Já existe um tipo de entrevista "
            "cadastrado com esse nome."
        )


    except sqlite3.Error:

        conexao.rollback()

        raise


    finally:

        conexao.close()


# ============================================================
# CONTAR PERGUNTAS
# ============================================================

def contar_perguntas_tipo(
    tipo_entrevista_id: int
) -> int:
    """
    Retorna a quantidade total de perguntas
    vinculadas ao tipo de entrevista.

    Inclui perguntas ativas e inativas.
    """

    _validar_id(
        tipo_entrevista_id
    )


    conexao = conectar_banco()

    cursor = conexao.cursor()


    try:

        cursor.execute(
            """
            SELECT
                COUNT(*) AS quantidade

            FROM perguntas

            WHERE tipo_entrevista_id = ?
            """,
            (
                tipo_entrevista_id,
            )
        )


        registro = cursor.fetchone()


        return int(
            registro["quantidade"]
        )


    finally:

        conexao.close()


# ============================================================
# CONTAR PERGUNTAS ATIVAS
# ============================================================

def contar_perguntas_ativas_tipo(
    tipo_entrevista_id: int
) -> int:
    """
    Retorna a quantidade de perguntas ativas
    vinculadas ao tipo de entrevista.

    Esta função é utilizada para impedir
    a inativação de um tipo que ainda possua
    perguntas disponíveis para uso.
    """

    _validar_id(
        tipo_entrevista_id
    )


    conexao = conectar_banco()

    cursor = conexao.cursor()


    try:

        cursor.execute(
            """
            SELECT
                COUNT(*) AS quantidade

            FROM perguntas

            WHERE tipo_entrevista_id = ?

              AND ativa = 1
            """,
            (
                tipo_entrevista_id,
            )
        )


        registro = cursor.fetchone()


        return int(
            registro["quantidade"]
        )


    finally:

        conexao.close()


# ============================================================
# CONTAR ENTREVISTAS
# ============================================================

def contar_entrevistas_tipo(
    tipo_entrevista_id: int
) -> int:
    """
    Retorna a quantidade de entrevistas
    relacionadas ao tipo.

    Esta informação é histórica.

    A existência de entrevistas anteriores
    NÃO impede que um tipo seja inativado.
    """

    _validar_id(
        tipo_entrevista_id
    )


    conexao = conectar_banco()

    cursor = conexao.cursor()


    try:

        cursor.execute(
            """
            SELECT
                COUNT(*) AS quantidade

            FROM entrevistas

            WHERE tipo_entrevista_id = ?
            """,
            (
                tipo_entrevista_id,
            )
        )


        registro = cursor.fetchone()


        return int(
            registro["quantidade"]
        )


    finally:

        conexao.close()


# ============================================================
# VERIFICAR USO
# ============================================================

def tipo_entrevista_em_uso(
    tipo_entrevista_id: int
) -> bool:
    """
    Verifica se o tipo de entrevista possui
    alguma referência no sistema.

    Considera:

    - perguntas;
    - entrevistas históricas.
    """

    quantidade_perguntas = (
        contar_perguntas_tipo(
            tipo_entrevista_id
        )
    )


    quantidade_entrevistas = (
        contar_entrevistas_tipo(
            tipo_entrevista_id
        )
    )


    return (
        quantidade_perguntas > 0
        or quantidade_entrevistas > 0
    )


# ============================================================
# ATIVAR TIPO
# ============================================================

def ativar_tipo_entrevista(
    tipo_entrevista_id: int
) -> bool:
    """
    Ativa um tipo de entrevista.
    """

    _validar_id(
        tipo_entrevista_id
    )


    tipo = buscar_tipo_entrevista(
        tipo_entrevista_id
    )


    if tipo is None:

        return False


    if tipo["ativo"]:

        return True


    return _alterar_status_tipo_entrevista(
        tipo_entrevista_id,
        True
    )


# ============================================================
# INATIVAR TIPO
# ============================================================

def inativar_tipo_entrevista(
    tipo_entrevista_id: int
) -> bool:
    """
    Inativa um tipo de entrevista.

    REGRA:

    O tipo NÃO pode ser inativado enquanto
    possuir perguntas ativas vinculadas.

    Perguntas inativas não impedem a operação.

    Entrevistas históricas também não impedem,
    pois devem continuar preservadas mesmo
    depois que um tipo deixa de ser oferecido.
    """

    _validar_id(
        tipo_entrevista_id
    )


    tipo = buscar_tipo_entrevista(
        tipo_entrevista_id
    )


    if tipo is None:

        return False


    # --------------------------------------------------------
    # JÁ ESTÁ INATIVO
    # --------------------------------------------------------

    if not tipo["ativo"]:

        return True


    # --------------------------------------------------------
    # VERIFICAR PERGUNTAS ATIVAS
    # --------------------------------------------------------

    quantidade_perguntas_ativas = (
        contar_perguntas_ativas_tipo(
            tipo_entrevista_id
        )
    )


    if quantidade_perguntas_ativas > 0:

        raise ValueError(
            "O tipo de entrevista não pode ser inativado "
            "porque possui perguntas ativas vinculadas."
        )


    # --------------------------------------------------------
    # INATIVAR
    # --------------------------------------------------------

    return _alterar_status_tipo_entrevista(
        tipo_entrevista_id,
        False
    )


# ============================================================
# ALTERAR STATUS
# ============================================================

def _alterar_status_tipo_entrevista(
    tipo_entrevista_id: int,
    ativo: bool
) -> bool:
    """
    Altera o status de um tipo de entrevista.
    """

    _validar_id(
        tipo_entrevista_id
    )


    conexao = conectar_banco()

    cursor = conexao.cursor()


    try:

        cursor.execute(
            """
            UPDATE tipos_entrevista

            SET ativo = ?

            WHERE id = ?
            """,
            (
                1
                if ativo
                else 0,

                tipo_entrevista_id
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
# DETALHES DO TIPO
# ============================================================

def obter_detalhes_tipo_entrevista(
    tipo_entrevista_id: int
) -> dict | None:
    """
    Retorna informações detalhadas sobre
    o tipo de entrevista.
    """

    _validar_id(
        tipo_entrevista_id
    )


    tipo = buscar_tipo_entrevista(
        tipo_entrevista_id
    )


    if tipo is None:

        return None


    quantidade_perguntas = (
        contar_perguntas_tipo(
            tipo_entrevista_id
        )
    )


    quantidade_perguntas_ativas = (
        contar_perguntas_ativas_tipo(
            tipo_entrevista_id
        )
    )


    quantidade_entrevistas = (
        contar_entrevistas_tipo(
            tipo_entrevista_id
        )
    )


    return {

        "id":
            tipo["id"],

        "nome":
            tipo["nome"],

        "ativo":
            tipo["ativo"],

        "quantidade_perguntas":
            quantidade_perguntas,

        "quantidade_perguntas_ativas":
            quantidade_perguntas_ativas,

        "quantidade_entrevistas":
            quantidade_entrevistas,

        "em_uso":
            (
                quantidade_perguntas > 0
                or quantidade_entrevistas > 0
            )

    }