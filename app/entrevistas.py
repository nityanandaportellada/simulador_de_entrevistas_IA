"""
entrevistas.py

Módulo responsável pelo gerenciamento das entrevistas
do Simulador de Entrevistas.

Versão: 0.2

Responsabilidades:

- criar entrevistas;
- buscar entrevistas;
- listar entrevistas de um usuário;
- listar todas as entrevistas;
- alterar status;
- finalizar entrevistas;
- cancelar entrevistas;
- registrar pontuação final;
- consultar quantidade de respostas.

O módulo não realiza análise por Inteligência Artificial.
Essa responsabilidade pertence ao módulo analise.py.
"""

import sqlite3

from datetime import (
    datetime,
    timezone
)

try:

    from .database import conectar_banco

    from .models import Entrevista

except ImportError:

    from database import conectar_banco

    from models import Entrevista


# ============================================================
# STATUS PERMITIDOS
# ============================================================

STATUS_ENTREVISTA = (

    "em_andamento",

    "finalizada",

    "em_analise",

    "avaliada",

    "erro_analise",

    "cancelada"

)


# ============================================================
# CRIAR ENTREVISTA
# ============================================================

def criar_entrevista(
    usuario_id: int,
    tipo_entrevista_id: int
) -> int:
    """
    Cria uma nova entrevista.

    A entrevista é criada inicialmente com o status
    "em_andamento".

    Retorna o ID da entrevista criada.
    """

    # --------------------------------------------------------
    # VALIDAR USUÁRIO
    # --------------------------------------------------------

    if usuario_id <= 0:

        raise ValueError(
            "O usuário informado é inválido."
        )


    # --------------------------------------------------------
    # VALIDAR TIPO DE ENTREVISTA
    # --------------------------------------------------------

    if tipo_entrevista_id <= 0:

        raise ValueError(
            "O tipo de entrevista informado é inválido."
        )


    conexao = conectar_banco()

    cursor = conexao.cursor()


    try:

        # ----------------------------------------------------
        # VERIFICAR USUÁRIO
        # ----------------------------------------------------

        cursor.execute(
            """
            SELECT id

            FROM usuarios

            WHERE id = ?

              AND ativo = 1
            """,
            (
                usuario_id,
            )
        )


        if cursor.fetchone() is None:

            raise ValueError(
                "Usuário não encontrado ou inativo."
            )


        # ----------------------------------------------------
        # VERIFICAR TIPO DE ENTREVISTA
        # ----------------------------------------------------

        cursor.execute(
            """
            SELECT id

            FROM tipos_entrevista

            WHERE id = ?

              AND ativo = 1
            """,
            (
                tipo_entrevista_id,
            )
        )


        if cursor.fetchone() is None:

            raise ValueError(
                "Tipo de entrevista não encontrado "
                "ou inativo."
            )


        # ----------------------------------------------------
        # CRIAR ENTREVISTA
        # ----------------------------------------------------

        cursor.execute(
            """
            INSERT INTO entrevistas (
                usuario_id,
                tipo_entrevista_id,
                status
            )

            VALUES (?, ?, 'em_andamento')
            """,
            (
                usuario_id,
                tipo_entrevista_id
            )
        )


        entrevista_id = (
            cursor.lastrowid
        )


        conexao.commit()


        return entrevista_id


    except (
        sqlite3.Error,
        ValueError
    ):

        conexao.rollback()

        raise


    finally:

        conexao.close()


# ============================================================
# BUSCAR ENTREVISTA
# ============================================================

def buscar_entrevista(
    entrevista_id: int
) -> Entrevista | None:
    """
    Busca uma entrevista pelo ID.

    Retorna um objeto Entrevista.

    Caso não seja encontrada, retorna None.
    """

    conexao = conectar_banco()

    cursor = conexao.cursor()


    try:

        cursor.execute(
            """
            SELECT *

            FROM entrevistas

            WHERE id = ?
            """,
            (
                entrevista_id,
            )
        )


        registro = cursor.fetchone()


        if registro is None:

            return None


        return _registro_para_entrevista(
            registro
        )


    finally:

        conexao.close()


# ============================================================
# LISTAR ENTREVISTAS DO USUÁRIO
# ============================================================

def listar_entrevistas_usuario(
    usuario_id: int
) -> list[Entrevista]:
    """
    Retorna todas as entrevistas pertencentes
    a determinado usuário.

    As entrevistas mais recentes aparecem primeiro.
    """

    conexao = conectar_banco()

    cursor = conexao.cursor()


    try:

        cursor.execute(
            """
            SELECT *

            FROM entrevistas

            WHERE usuario_id = ?

            ORDER BY data_inicio DESC
            """,
            (
                usuario_id,
            )
        )


        registros = cursor.fetchall()


        return [

            _registro_para_entrevista(
                registro
            )

            for registro in registros
        ]


    finally:

        conexao.close()


# ============================================================
# LISTAR TODAS AS ENTREVISTAS
# ============================================================

def listar_entrevistas() -> list[Entrevista]:
    """
    Retorna todas as entrevistas cadastradas.

    Esta função é utilizada principalmente
    pelo perfil Administrador.
    """

    conexao = conectar_banco()

    cursor = conexao.cursor()


    try:

        cursor.execute(
            """
            SELECT *

            FROM entrevistas

            ORDER BY data_inicio DESC
            """
        )


        registros = cursor.fetchall()


        return [

            _registro_para_entrevista(
                registro
            )

            for registro in registros
        ]


    finally:

        conexao.close()


# ============================================================
# ALTERAR STATUS
# ============================================================

def alterar_status_entrevista(
    entrevista_id: int,
    novo_status: str
) -> bool:
    """
    Altera o status de uma entrevista.
    """

    if novo_status not in STATUS_ENTREVISTA:

        raise ValueError(
            f"Status de entrevista inválido: {novo_status}"
        )


    conexao = conectar_banco()

    cursor = conexao.cursor()


    try:

        cursor.execute(
            """
            UPDATE entrevistas

            SET status = ?

            WHERE id = ?
            """,
            (
                novo_status,
                entrevista_id
            )
        )


        conexao.commit()


        return cursor.rowcount > 0


    except sqlite3.Error:

        conexao.rollback()

        raise


    finally:

        conexao.close()


# ============================================================
# FINALIZAR ENTREVISTA
# ============================================================

def finalizar_entrevista(
    entrevista_id: int
) -> bool:
    """
    Finaliza uma entrevista.

    Registra a data/hora da finalização em UTC
    e altera o status para "finalizada".

    Somente entrevistas em andamento podem
    ser finalizadas.
    """

    conexao = conectar_banco()

    cursor = conexao.cursor()


    try:

        # ----------------------------------------------------
        # VERIFICAR ENTREVISTA
        # ----------------------------------------------------

        cursor.execute(
            """
            SELECT status

            FROM entrevistas

            WHERE id = ?
            """,
            (
                entrevista_id,
            )
        )


        registro = cursor.fetchone()


        if registro is None:

            raise ValueError(
                "Entrevista não encontrada."
            )


        # ----------------------------------------------------
        # VERIFICAR STATUS
        # ----------------------------------------------------

        if registro["status"] != "em_andamento":

            raise ValueError(
                "Somente entrevistas em andamento "
                "podem ser finalizadas."
            )


        # ----------------------------------------------------
        # DATA/HORA UTC
        # ----------------------------------------------------

        data_fim = (
            datetime.now(
                timezone.utc
            ).strftime(
                "%Y-%m-%d %H:%M:%S"
            )
        )


        # ----------------------------------------------------
        # FINALIZAR
        # ----------------------------------------------------

        cursor.execute(
            """
            UPDATE entrevistas

            SET
                status = 'finalizada',
                data_fim = ?

            WHERE id = ?
            """,
            (
                data_fim,
                entrevista_id
            )
        )


        conexao.commit()


        return cursor.rowcount > 0


    except (
        sqlite3.Error,
        ValueError
    ):

        conexao.rollback()

        raise


    finally:

        conexao.close()


# ============================================================
# CANCELAR ENTREVISTA
# ============================================================

def cancelar_entrevista(
    entrevista_id: int
) -> bool:
    """
    Cancela uma entrevista em andamento.

    Registra a data/hora do cancelamento em UTC.

    Entrevistas finalizadas, avaliadas ou canceladas
    não podem ser canceladas novamente.
    """

    conexao = conectar_banco()

    cursor = conexao.cursor()


    try:

        # ----------------------------------------------------
        # VERIFICAR ENTREVISTA
        # ----------------------------------------------------

        cursor.execute(
            """
            SELECT status

            FROM entrevistas

            WHERE id = ?
            """,
            (
                entrevista_id,
            )
        )


        registro = cursor.fetchone()


        if registro is None:

            raise ValueError(
                "Entrevista não encontrada."
            )


        # ----------------------------------------------------
        # VERIFICAR STATUS
        # ----------------------------------------------------

        if registro["status"] != "em_andamento":

            raise ValueError(
                "Somente entrevistas em andamento "
                "podem ser canceladas."
            )


        # ----------------------------------------------------
        # DATA/HORA UTC
        # ----------------------------------------------------

        data_fim = (
            datetime.now(
                timezone.utc
            ).strftime(
                "%Y-%m-%d %H:%M:%S"
            )
        )


        # ----------------------------------------------------
        # CANCELAR
        # ----------------------------------------------------

        cursor.execute(
            """
            UPDATE entrevistas

            SET
                status = 'cancelada',
                data_fim = ?

            WHERE id = ?
            """,
            (
                data_fim,
                entrevista_id
            )
        )


        conexao.commit()


        return cursor.rowcount > 0


    except (
        sqlite3.Error,
        ValueError
    ):

        conexao.rollback()

        raise


    finally:

        conexao.close()


# ============================================================
# REGISTRAR PONTUAÇÃO FINAL
# ============================================================

def registrar_pontuacao_final(
    entrevista_id: int,
    pontuacao: float
) -> bool:
    """
    Registra a pontuação final de uma entrevista.

    A pontuação deve estar entre 0 e 10.
    """

    if pontuacao < 0 or pontuacao > 10:

        raise ValueError(
            "A pontuação deve estar entre 0 e 10."
        )


    conexao = conectar_banco()

    cursor = conexao.cursor()


    try:

        cursor.execute(
            """
            UPDATE entrevistas

            SET pontuacao_final = ?

            WHERE id = ?
            """,
            (
                pontuacao,
                entrevista_id
            )
        )


        conexao.commit()


        return cursor.rowcount > 0


    except sqlite3.Error:

        conexao.rollback()

        raise


    finally:

        conexao.close()


# ============================================================
# CONTAR RESPOSTAS
# ============================================================

def contar_respostas(
    entrevista_id: int
) -> int:
    """
    Retorna a quantidade de respostas registradas
    para determinada entrevista.
    """

    conexao = conectar_banco()

    cursor = conexao.cursor()


    try:

        cursor.execute(
            """
            SELECT COUNT(*) AS quantidade

            FROM respostas

            WHERE entrevista_id = ?
            """,
            (
                entrevista_id,
            )
        )


        registro = cursor.fetchone()


        return int(
            registro["quantidade"]
        )


    finally:

        conexao.close()


# ============================================================
# CONVERTER REGISTRO
# ============================================================

def _registro_para_entrevista(
    registro: sqlite3.Row
) -> Entrevista:
    """
    Converte um registro SQLite
    em objeto Entrevista.
    """

    return Entrevista(

        id=registro[
            "id"
        ],

        usuario_id=registro[
            "usuario_id"
        ],

        tipo_entrevista_id=registro[
            "tipo_entrevista_id"
        ],

        data_inicio=registro[
            "data_inicio"
        ],

        data_fim=registro[
            "data_fim"
        ],

        status=registro[
            "status"
        ],

        pontuacao_final=registro[
            "pontuacao_final"
        ],

        observacoes=registro[
            "observacoes"
        ]
    )