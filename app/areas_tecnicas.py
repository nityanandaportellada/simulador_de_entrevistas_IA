"""
areas_tecnicas.py

Módulo responsável pelo gerenciamento das áreas técnicas
do Simulador de Entrevistas.

Responsabilidades:

- cadastrar áreas técnicas;
- listar áreas técnicas;
- buscar área por ID;
- editar áreas;
- ativar áreas;
- inativar áreas;
- criar automaticamente a subárea Geral;
- proteger vínculos com perguntas técnicas.

Exemplos de áreas iniciais:

- Direito;
- Psicologia;
- Administração;
- Economia;
- Ciências Contábeis;
- Tecnologia.

O acesso ao banco de dados é realizado através
do módulo database.py.
"""

import sqlite3


try:

    from .database import conectar_banco

    from .models import AreaTecnica


except ImportError:

    from database import conectar_banco

    from models import AreaTecnica


# ============================================================
# CONVERTER REGISTRO EM OBJETO
# ============================================================

def _registro_para_area(
    registro
) -> AreaTecnica:
    """
    Converte um registro sqlite3.Row
    em um objeto AreaTecnica.
    """

    return AreaTecnica(

        id=registro[
            "id"
        ],

        nome=registro[
            "nome"
        ],

        descricao=registro[
            "descricao"
        ],

        ativo=bool(
            registro[
                "ativo"
            ]
        ),

        ordem=registro[
            "ordem"
        ],

        data_criacao=registro[
            "data_criacao"
        ]

    )


# ============================================================
# VALIDAR ID
# ============================================================

def _validar_id(
    valor: int,
    campo: str
) -> None:
    """
    Valida identificadores numéricos.
    """

    if (
        valor is None
        or valor <= 0
    ):

        raise ValueError(
            f"{campo} inválido."
        )


# ============================================================
# VALIDAR NOME
# ============================================================

def _validar_nome(
    nome: str
) -> str:
    """
    Valida e normaliza o nome da área.
    """

    if nome is None:

        raise ValueError(
            "O nome da área é obrigatório."
        )


    nome = nome.strip()


    if len(nome) < 2:

        raise ValueError(
            "O nome da área deve possuir "
            "pelo menos 2 caracteres."
        )


    if len(nome) > 150:

        raise ValueError(
            "O nome da área deve possuir "
            "no máximo 150 caracteres."
        )


    return nome


# ============================================================
# VALIDAR ORDEM
# ============================================================

def _validar_ordem(
    ordem: int | None
) -> None:
    """
    Valida a ordem de exibição.
    """

    if (
        ordem is not None
        and ordem < 0
    ):

        raise ValueError(
            "A ordem não pode ser negativa."
        )


# ============================================================
# VERIFICAR NOME DUPLICADO
# ============================================================

def _nome_duplicado(
    cursor,
    nome: str,
    ignorar_id: int | None = None
) -> bool:
    """
    Verifica se já existe outra área
    com o mesmo nome.
    """

    if ignorar_id is None:

        cursor.execute(
            """
            SELECT id

            FROM areas_tecnicas

            WHERE LOWER(nome) =
                LOWER(?)

            LIMIT 1
            """,
            (
                nome,
            )
        )


    else:

        cursor.execute(
            """
            SELECT id

            FROM areas_tecnicas

            WHERE LOWER(nome) =
                LOWER(?)

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


# ============================================================
# BUSCAR ÁREA
# ============================================================

def buscar_area_tecnica(
    area_id: int
) -> AreaTecnica | None:
    """
    Busca uma área técnica pelo ID.
    """

    _validar_id(
        area_id,
        "ID da área"
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
                ativo,
                ordem,
                data_criacao

            FROM areas_tecnicas

            WHERE id = ?
            """,
            (
                area_id,
            )
        )


        registro = cursor.fetchone()


        if registro is None:

            return None


        return _registro_para_area(
            registro
        )


    finally:

        conexao.close()


# ============================================================
# LISTAR ÁREAS
# ============================================================

def listar_areas_tecnicas(
    somente_ativas: bool = True
) -> list[AreaTecnica]:
    """
    Lista as áreas técnicas cadastradas.

    Quando somente_ativas for True,
    retorna apenas áreas ativas.
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
                    ativo,
                    ordem,
                    data_criacao

                FROM areas_tecnicas

                WHERE ativo = 1

                ORDER BY

                    COALESCE(
                        ordem,
                        999999
                    ),

                    nome,
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
                    ativo,
                    ordem,
                    data_criacao

                FROM areas_tecnicas

                ORDER BY

                    COALESCE(
                        ordem,
                        999999
                    ),

                    nome,
                    id
                """
            )


        registros = cursor.fetchall()


        return [

            _registro_para_area(
                registro
            )

            for registro
            in registros

        ]


    finally:

        conexao.close()


# ============================================================
# CADASTRAR ÁREA
# ============================================================

def cadastrar_area_tecnica(
    area: AreaTecnica
) -> int:
    """
    Cadastra uma nova área técnica.

    Ao criar a área, a subárea protegida
    "Geral" é criada automaticamente.

    Retorna o ID da nova área.
    """

    nome = _validar_nome(
        area.nome
    )


    _validar_ordem(
        area.ordem
    )


    descricao = area.descricao


    if descricao is not None:

        descricao = (
            descricao.strip()
            or None
        )


    conexao = conectar_banco()

    cursor = conexao.cursor()


    try:

        cursor.execute(
            """
            BEGIN IMMEDIATE
            """
        )


        if _nome_duplicado(
            cursor,
            nome
        ):

            raise ValueError(
                "Já existe uma área técnica "
                "com este nome."
            )


        cursor.execute(
            """
            INSERT INTO areas_tecnicas (

                nome,
                descricao,
                ativo,
                ordem

            )

            VALUES (
                ?,
                ?,
                1,
                ?
            )
            """,
            (
                nome,
                descricao,
                area.ordem
            )
        )


        area_id = cursor.lastrowid


        # ----------------------------------------------------
        # CRIAR SUBÁREA GERAL
        # ----------------------------------------------------

        cursor.execute(
            """
            INSERT INTO subareas_tecnicas (

                area_tecnica_id,
                nome,
                descricao,
                eh_geral,
                ativo,
                ordem

            )

            VALUES (
                ?,
                'Geral',
                ?,
                1,
                1,
                1
            )
            """,
            (
                area_id,

                (
                    "Subárea padrão destinada "
                    "a perguntas gerais da área."
                )
            )
        )


        conexao.commit()


        return int(
            area_id
        )


    except (
        sqlite3.Error,
        ValueError
    ):

        conexao.rollback()

        raise


    finally:

        conexao.close()


# ============================================================
# EDITAR ÁREA
# ============================================================

def editar_area_tecnica(
    area_id: int,
    area: AreaTecnica
) -> bool:
    """
    Atualiza os dados administrativos
    de uma área técnica.

    O status ativo/inativo não é alterado
    por esta função.
    """

    _validar_id(
        area_id,
        "ID da área"
    )


    nome = _validar_nome(
        area.nome
    )


    _validar_ordem(
        area.ordem
    )


    descricao = area.descricao


    if descricao is not None:

        descricao = (
            descricao.strip()
            or None
        )


    conexao = conectar_banco()

    cursor = conexao.cursor()


    try:

        cursor.execute(
            """
            BEGIN IMMEDIATE
            """
        )


        cursor.execute(
            """
            SELECT id

            FROM areas_tecnicas

            WHERE id = ?
            """,
            (
                area_id,
            )
        )


        if cursor.fetchone() is None:

            conexao.rollback()

            return False


        if _nome_duplicado(
            cursor,
            nome,
            area_id
        ):

            raise ValueError(
                "Já existe outra área técnica "
                "com este nome."
            )


        cursor.execute(
            """
            UPDATE areas_tecnicas

            SET

                nome = ?,
                descricao = ?,
                ordem = ?

            WHERE id = ?
            """,
            (
                nome,
                descricao,
                area.ordem,
                area_id
            )
        )


        conexao.commit()


        return True


    except (
        sqlite3.Error,
        ValueError
    ):

        conexao.rollback()

        raise


    finally:

        conexao.close()


# ============================================================
# CONTAR PERGUNTAS ATIVAS DA ÁREA
# ============================================================

def contar_perguntas_ativas_area(
    area_id: int
) -> int:
    """
    Retorna a quantidade de perguntas ativas
    vinculadas direta ou indiretamente à área.
    """

    _validar_id(
        area_id,
        "ID da área"
    )


    conexao = conectar_banco()

    cursor = conexao.cursor()


    try:

        cursor.execute(
            """
            SELECT COUNT(*) AS quantidade

            FROM perguntas p

            WHERE p.ativa = 1

              AND (

                    p.area_tecnica_id = ?

                    OR

                    p.subarea_tecnica_id IN (

                        SELECT
                            s.id

                        FROM subareas_tecnicas s

                        WHERE
                            s.area_tecnica_id = ?

                    )

              )
            """,
            (
                area_id,
                area_id
            )
        )


        registro = cursor.fetchone()


        return int(
            registro[
                "quantidade"
            ]
        )


    finally:

        conexao.close()


# ============================================================
# INATIVAR ÁREA
# ============================================================

def inativar_area_tecnica(
    area_id: int
) -> bool:
    """
    Inativa uma área técnica.

    A operação é bloqueada quando existem
    perguntas ativas vinculadas à área ou
    às suas subáreas.
    """

    _validar_id(
        area_id,
        "ID da área"
    )


    conexao = conectar_banco()

    cursor = conexao.cursor()


    try:

        cursor.execute(
            """
            BEGIN IMMEDIATE
            """
        )


        cursor.execute(
            """
            SELECT

                id,
                ativo

            FROM areas_tecnicas

            WHERE id = ?
            """,
            (
                area_id,
            )
        )


        registro = cursor.fetchone()


        if registro is None:

            conexao.rollback()

            return False


        if not bool(
            registro[
                "ativo"
            ]
        ):

            conexao.commit()

            return True


        cursor.execute(
            """
            SELECT COUNT(*) AS quantidade

            FROM perguntas p

            WHERE p.ativa = 1

              AND (

                    p.area_tecnica_id = ?

                    OR

                    p.subarea_tecnica_id IN (

                        SELECT
                            s.id

                        FROM subareas_tecnicas s

                        WHERE
                            s.area_tecnica_id = ?

                    )

              )
            """,
            (
                area_id,
                area_id
            )
        )


        quantidade = int(
            cursor.fetchone()[
                "quantidade"
            ]
        )


        if quantidade > 0:

            raise ValueError(
                "A área não pode ser inativada "
                "porque possui perguntas ativas "
                "vinculadas."
            )


        cursor.execute(
            """
            UPDATE areas_tecnicas

            SET ativo = 0

            WHERE id = ?
            """,
            (
                area_id,
            )
        )


        conexao.commit()


        return True


    except (
        sqlite3.Error,
        ValueError
    ):

        conexao.rollback()

        raise


    finally:

        conexao.close()


# ============================================================
# ATIVAR ÁREA
# ============================================================

def ativar_area_tecnica(
    area_id: int
) -> bool:
    """
    Ativa uma área técnica anteriormente
    inativada.
    """

    _validar_id(
        area_id,
        "ID da área"
    )


    conexao = conectar_banco()

    cursor = conexao.cursor()


    try:

        cursor.execute(
            """
            BEGIN IMMEDIATE
            """
        )


        cursor.execute(
            """
            SELECT id

            FROM areas_tecnicas

            WHERE id = ?
            """,
            (
                area_id,
            )
        )


        if cursor.fetchone() is None:

            conexao.rollback()

            return False


        # ----------------------------------------------------
        # GARANTIR QUE A SUBÁREA GERAL EXISTA
        # ----------------------------------------------------

        cursor.execute(
            """
            SELECT id

            FROM subareas_tecnicas

            WHERE area_tecnica_id = ?
              AND eh_geral = 1

            LIMIT 1
            """,
            (
                area_id,
            )
        )


        geral = cursor.fetchone()


        if geral is None:

            cursor.execute(
                """
                INSERT INTO subareas_tecnicas (

                    area_tecnica_id,
                    nome,
                    descricao,
                    eh_geral,
                    ativo,
                    ordem

                )

                VALUES (
                    ?,
                    'Geral',
                    ?,
                    1,
                    1,
                    1
                )
                """,
                (
                    area_id,

                    (
                        "Subárea padrão destinada "
                        "a perguntas gerais da área."
                    )
                )
            )


        cursor.execute(
            """
            UPDATE areas_tecnicas

            SET ativo = 1

            WHERE id = ?
            """,
            (
                area_id,
            )
        )


        conexao.commit()


        return True


    except sqlite3.Error:

        conexao.rollback()

        raise


    finally:

        conexao.close()