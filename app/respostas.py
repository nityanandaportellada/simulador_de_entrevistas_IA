"""
respostas.py

Módulo responsável pelo gerenciamento das respostas
fornecidas pelos estudantes durante as entrevistas.

Versão: 0.3

Responsabilidades:

- salvar respostas;
- buscar respostas;
- listar respostas de uma entrevista;
- disponibilizar o snapshot histórico da pergunta;
- editar respostas enquanto a entrevista estiver aberta;
- excluir respostas enquanto a entrevista estiver aberta;
- verificar se determinada pergunta já foi respondida;
- tratar com segurança respostas concorrentes para
  a mesma pergunta.

As respostas somente poderão ser alteradas enquanto
a entrevista estiver com status "em_andamento".

CONCORRÊNCIA:

A tabela respostas possui restrição UNIQUE para:

    entrevista_id + pergunta_id

A verificação realizada antes do INSERT melhora a
mensagem apresentada em situações normais.

Entretanto, duas requisições concorrentes podem executar
a verificação ao mesmo tempo.

Nesse cenário, o próprio SQLite garante a integridade
através da restrição UNIQUE.

Quando essa violação específica ocorrer, este módulo
converte o sqlite3.IntegrityError em ValueError para que
a camada HTTP retorne um erro de domínio controlado,
em vez de HTTP 500.
"""

import sqlite3


try:

    from .database import conectar_banco

    from .models import Resposta


except ImportError:

    from database import conectar_banco

    from models import Resposta


# ============================================================
# SALVAR RESPOSTA
# ============================================================

def salvar_resposta(
    entrevista_id: int,
    pergunta_id: int,
    texto_resposta: str,
    tempo_resposta: int | None = None
) -> int:
    """
    Registra uma resposta no banco.

    Retorna o ID da resposta criada.

    Em caso de duas gravações concorrentes para a mesma
    combinação entrevista + pergunta, a restrição UNIQUE
    do SQLite impede a duplicidade.

    Essa violação específica é convertida em ValueError
    para tratamento adequado pela API.
    """

    # --------------------------------------------------------
    # VALIDAÇÕES BÁSICAS
    # --------------------------------------------------------

    if entrevista_id <= 0:

        raise ValueError(
            "A entrevista informada é inválida."
        )


    if pergunta_id <= 0:

        raise ValueError(
            "A pergunta informada é inválida."
        )


    if texto_resposta is None:

        raise ValueError(
            "A resposta é obrigatória."
        )


    if not texto_resposta.strip():

        raise ValueError(
            "A resposta não pode estar vazia."
        )


    if (
        tempo_resposta is not None
        and tempo_resposta < 0
    ):

        raise ValueError(
            "O tempo de resposta não pode ser negativo."
        )


    conexao = conectar_banco()

    cursor = conexao.cursor()


    try:

        # ----------------------------------------------------
        # VERIFICAR ENTREVISTA
        # ----------------------------------------------------

        cursor.execute(
            """
            SELECT
                id,
                tipo_entrevista_id,
                status

            FROM entrevistas

            WHERE id = ?
            """,
            (
                entrevista_id,
            )
        )


        entrevista = cursor.fetchone()


        if entrevista is None:

            raise ValueError(
                "Entrevista não encontrada."
            )


        if entrevista["status"] != "em_andamento":

            raise ValueError(
                "Não é possível registrar respostas "
                "em uma entrevista que não esteja "
                "em andamento."
            )


        # ----------------------------------------------------
        # VERIFICAR PERGUNTA
        # ----------------------------------------------------

        cursor.execute(
            """
            SELECT
                id,
                tipo_entrevista_id,
                ativa

            FROM perguntas

            WHERE id = ?
            """,
            (
                pergunta_id,
            )
        )


        pergunta = cursor.fetchone()


        if pergunta is None:

            raise ValueError(
                "Pergunta não encontrada."
            )


        if pergunta["ativa"] != 1:

            raise ValueError(
                "A pergunta informada está inativa."
            )


        # ----------------------------------------------------
        # VERIFICAR SE A PERGUNTA PERTENCE AO TIPO
        # DA ENTREVISTA
        # ----------------------------------------------------

        if (
            pergunta["tipo_entrevista_id"]
            != entrevista["tipo_entrevista_id"]
        ):

            raise ValueError(
                "A pergunta não pertence ao tipo "
                "desta entrevista."
            )


        # ----------------------------------------------------
        # VERIFICAR RESPOSTA DUPLICADA
        #
        # Esta verificação cobre o fluxo normal.
        #
        # A restrição UNIQUE do banco continua sendo
        # responsável por proteger contra concorrência.
        # ----------------------------------------------------

        cursor.execute(
            """
            SELECT id

            FROM respostas

            WHERE entrevista_id = ?
              AND pergunta_id = ?
            """,
            (
                entrevista_id,
                pergunta_id
            )
        )


        if cursor.fetchone() is not None:

            raise ValueError(
                "Esta pergunta já possui uma resposta "
                "registrada nesta entrevista."
            )


        # ----------------------------------------------------
        # SALVAR
        # ----------------------------------------------------

        cursor.execute(
            """
            INSERT INTO respostas (
                entrevista_id,
                pergunta_id,
                texto_resposta,
                tempo_resposta
            )

            VALUES (?, ?, ?, ?)
            """,
            (
                entrevista_id,
                pergunta_id,
                texto_resposta.strip(),
                tempo_resposta
            )
        )


        resposta_id = cursor.lastrowid


        conexao.commit()


        return resposta_id


    # ========================================================
    # CONFLITO DE CONCORRÊNCIA
    # ========================================================

    except sqlite3.IntegrityError as erro:

        conexao.rollback()


        mensagem_erro = str(
            erro
        )


        # ----------------------------------------------------
        # DUPLICIDADE:
        #
        # UNIQUE (
        #     entrevista_id,
        #     pergunta_id
        # )
        #
        # Duas requisições podem passar pelo SELECT acima
        # simultaneamente.
        #
        # Nesse caso, somente uma consegue realizar o INSERT.
        # A segunda chega aqui.
        # ----------------------------------------------------

        if (
            "UNIQUE constraint failed"
            in mensagem_erro

            and "respostas.entrevista_id"
            in mensagem_erro

            and "respostas.pergunta_id"
            in mensagem_erro
        ):

            raise ValueError(
                "Esta pergunta já possui uma resposta "
                "registrada nesta entrevista."
            ) from erro


        # ----------------------------------------------------
        # OUTRAS VIOLAÇÕES DE INTEGRIDADE
        #
        # Não devem ser escondidas como se fossem
        # duplicidade de resposta.
        # ----------------------------------------------------

        raise


    except ValueError:

        conexao.rollback()

        raise


    except sqlite3.Error:

        conexao.rollback()

        raise


    finally:

        conexao.close()


# ============================================================
# BUSCAR RESPOSTA
# ============================================================

def buscar_resposta(
    resposta_id: int
) -> Resposta | None:
    """
    Busca uma resposta pelo ID.
    """

    conexao = conectar_banco()

    cursor = conexao.cursor()


    try:

        cursor.execute(
            """
            SELECT *

            FROM respostas

            WHERE id = ?
            """,
            (
                resposta_id,
            )
        )


        registro = cursor.fetchone()


        if registro is None:

            return None


        return _registro_para_resposta(
            registro
        )


    finally:

        conexao.close()


# ============================================================
# BUSCAR RESPOSTA DA PERGUNTA
# ============================================================

def buscar_resposta_pergunta(
    entrevista_id: int,
    pergunta_id: int
) -> Resposta | None:
    """
    Retorna a resposta de uma determinada pergunta
    dentro de uma entrevista.
    """

    conexao = conectar_banco()

    cursor = conexao.cursor()


    try:

        cursor.execute(
            """
            SELECT *

            FROM respostas

            WHERE entrevista_id = ?
              AND pergunta_id = ?
            """,
            (
                entrevista_id,
                pergunta_id
            )
        )


        registro = cursor.fetchone()


        if registro is None:

            return None


        return _registro_para_resposta(
            registro
        )


    finally:

        conexao.close()


# ============================================================
# BUSCAR SNAPSHOT HISTÓRICO DA RESPOSTA
# ============================================================

def buscar_snapshot_resposta(
    resposta_id: int
) -> dict | None:
    """
    Recupera a resposta juntamente com o snapshot
    histórico da pergunta utilizado no momento em
    que a resposta foi registrada.

    Os dados retornados não dependem do estado atual
    da tabela perguntas.

    Isso garante que alterações administrativas
    posteriores não modifiquem entrevistas antigas.
    """

    if resposta_id <= 0:

        raise ValueError(
            "O ID da resposta é inválido."
        )


    conexao = conectar_banco()

    cursor = conexao.cursor()


    try:

        cursor.execute(
            """
            SELECT
                id,
                entrevista_id,
                pergunta_id,
                texto_resposta,
                tempo_resposta,
                data_resposta,
                pergunta_texto_aplicado,
                exemplo_esperado_aplicado,
                competencia_id_aplicada,
                competencia_nome_aplicada,
                peso_pergunta_aplicado,
                usa_star_aplicado,
                ordem_pergunta_aplicada

            FROM respostas

            WHERE id = ?
            """,
            (
                resposta_id,
            )
        )


        registro = cursor.fetchone()


        if registro is None:

            return None


        if (
            registro["pergunta_texto_aplicado"] is None
            or registro["competencia_id_aplicada"] is None
            or registro["competencia_nome_aplicada"] is None
            or registro["peso_pergunta_aplicado"] is None
            or registro["usa_star_aplicado"] is None
        ):

            raise ValueError(
                "A resposta não possui snapshot histórico "
                "completo da pergunta."
            )


        return {

            "id":
                registro["id"],

            "resposta_id":
                registro["id"],

            "entrevista_id":
                registro["entrevista_id"],

            "pergunta_id":
                registro["pergunta_id"],

            "pergunta":
                registro["pergunta_texto_aplicado"],

            "exemplo_esperado":
                registro["exemplo_esperado_aplicado"],

            "competencia_id":
                registro["competencia_id_aplicada"],

            "competencia":
                registro["competencia_nome_aplicada"],

            "peso_pergunta":
                registro["peso_pergunta_aplicado"],

            "usa_star":
                bool(
                    registro["usa_star_aplicado"]
                ),

            "ordem_pergunta":
                registro["ordem_pergunta_aplicada"],

            "texto_resposta":
                registro["texto_resposta"],

            "tempo_resposta":
                registro["tempo_resposta"],

            "data_resposta":
                registro["data_resposta"]

        }


    finally:

        conexao.close()


# ============================================================
# LISTAR RESPOSTAS DA ENTREVISTA
# ============================================================

def listar_respostas_entrevista(
    entrevista_id: int
) -> list[Resposta]:
    """
    Retorna todas as respostas pertencentes
    a uma entrevista.

    As respostas são ordenadas pela ordem
    histórica armazenada no snapshot da pergunta.
    """

    conexao = conectar_banco()

    cursor = conexao.cursor()


    try:

        cursor.execute(
            """
            SELECT r.*

            FROM respostas r

            WHERE r.entrevista_id = ?

            ORDER BY
                COALESCE(
                    r.ordem_pergunta_aplicada,
                    999999
                ),
                r.id
            """,
            (
                entrevista_id,
            )
        )


        registros = cursor.fetchall()


        return [

            _registro_para_resposta(
                registro
            )

            for registro in registros

        ]


    finally:

        conexao.close()


# ============================================================
# EDITAR RESPOSTA
# ============================================================

def editar_resposta(
    resposta_id: int,
    novo_texto: str,
    tempo_resposta: int | None = None
) -> bool:
    """
    Altera uma resposta existente.

    Somente respostas de entrevistas em andamento
    podem ser alteradas.
    """

    if novo_texto is None:

        raise ValueError(
            "A resposta é obrigatória."
        )


    if not novo_texto.strip():

        raise ValueError(
            "A resposta não pode estar vazia."
        )


    if (
        tempo_resposta is not None
        and tempo_resposta < 0
    ):

        raise ValueError(
            "O tempo de resposta não pode ser negativo."
        )


    conexao = conectar_banco()

    cursor = conexao.cursor()


    try:

        # ----------------------------------------------------
        # VERIFICAR STATUS DA ENTREVISTA
        # ----------------------------------------------------

        cursor.execute(
            """
            SELECT e.status

            FROM respostas r

            INNER JOIN entrevistas e
                ON e.id = r.entrevista_id

            WHERE r.id = ?
            """,
            (
                resposta_id,
            )
        )


        registro = cursor.fetchone()


        if registro is None:

            raise ValueError(
                "Resposta não encontrada."
            )


        if registro["status"] != "em_andamento":

            raise ValueError(
                "A resposta não pode ser alterada porque "
                "a entrevista já foi encerrada."
            )


        # ----------------------------------------------------
        # ATUALIZAR RESPOSTA
        # ----------------------------------------------------

        cursor.execute(
            """
            UPDATE respostas

            SET
                texto_resposta = ?,
                tempo_resposta = ?

            WHERE id = ?
            """,
            (
                novo_texto.strip(),
                tempo_resposta,
                resposta_id
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
# EXCLUIR RESPOSTA
# ============================================================

def excluir_resposta(
    resposta_id: int
) -> bool:
    """
    Exclui uma resposta.

    Somente respostas de entrevistas em andamento
    podem ser excluídas.
    """

    conexao = conectar_banco()

    cursor = conexao.cursor()


    try:

        cursor.execute(
            """
            SELECT e.status

            FROM respostas r

            INNER JOIN entrevistas e
                ON e.id = r.entrevista_id

            WHERE r.id = ?
            """,
            (
                resposta_id,
            )
        )


        registro = cursor.fetchone()


        if registro is None:

            return False


        if registro["status"] != "em_andamento":

            raise ValueError(
                "A resposta não pode ser excluída porque "
                "a entrevista já foi encerrada."
            )


        cursor.execute(
            """
            DELETE FROM respostas

            WHERE id = ?
            """,
            (
                resposta_id,
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
# VERIFICAR SE PERGUNTA FOI RESPONDIDA
# ============================================================

def pergunta_respondida(
    entrevista_id: int,
    pergunta_id: int
) -> bool:
    """
    Verifica se uma pergunta já possui resposta
    dentro da entrevista.
    """

    conexao = conectar_banco()

    cursor = conexao.cursor()


    try:

        cursor.execute(
            """
            SELECT 1

            FROM respostas

            WHERE entrevista_id = ?
              AND pergunta_id = ?

            LIMIT 1
            """,
            (
                entrevista_id,
                pergunta_id
            )
        )


        return cursor.fetchone() is not None


    finally:

        conexao.close()


# ============================================================
# CONTAR RESPOSTAS
# ============================================================

def contar_respostas_entrevista(
    entrevista_id: int
) -> int:
    """
    Retorna a quantidade de respostas existentes
    em uma entrevista.
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


        return registro["quantidade"]


    finally:

        conexao.close()


# ============================================================
# CONVERTER REGISTRO
# ============================================================

def _registro_para_resposta(
    registro: sqlite3.Row
) -> Resposta:
    """
    Converte um registro SQLite em objeto Resposta.
    """

    return Resposta(

        id=registro["id"],

        entrevista_id=registro[
            "entrevista_id"
        ],

        pergunta_id=registro[
            "pergunta_id"
        ],

        texto_resposta=registro[
            "texto_resposta"
        ],

        tempo_resposta=registro[
            "tempo_resposta"
        ],

        data_resposta=registro[
            "data_resposta"
        ]

    )