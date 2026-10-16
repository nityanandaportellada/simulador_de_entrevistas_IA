"""
respostas.py

Módulo responsável pelo gerenciamento das respostas
fornecidas pelos estudantes durante as entrevistas.

Responsabilidades:

- salvar respostas;
- validar se a pergunta pertence à entrevista;
- utilizar o snapshot congelado da pergunta;
- buscar respostas;
- listar respostas de uma entrevista;
- disponibilizar o snapshot histórico da pergunta;
- editar respostas enquanto a entrevista estiver aberta;
- excluir respostas enquanto a entrevista estiver aberta;
- verificar se determinada pergunta já foi respondida;
- contar respostas de uma entrevista;
- tratar tentativas simultâneas de resposta duplicada.

A partir da implementação de entrevista_perguntas,
uma resposta somente pode ser registrada para uma
pergunta que tenha sido congelada no início daquela
entrevista.

Isso significa que o sistema não depende mais do estado
atual do cadastro de perguntas durante uma entrevista.
"""

import sqlite3


try:

    from .database import conectar_banco

    from .models import Resposta


except ImportError:

    from database import conectar_banco

    from models import Resposta


# ============================================================
# VALIDAR ID
# ============================================================

def _validar_id(
    valor: int | None,
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
# VALIDAR TEXTO DA RESPOSTA
# ============================================================

def _validar_texto_resposta(
    texto_resposta: str
) -> str:
    """
    Valida e normaliza o texto da resposta.
    """

    if texto_resposta is None:

        raise ValueError(
            "A resposta é obrigatória."
        )


    texto = texto_resposta.strip()


    if not texto:

        raise ValueError(
            "A resposta não pode estar vazia."
        )


    return texto


# ============================================================
# VALIDAR TEMPO
# ============================================================

def _validar_tempo_resposta(
    tempo_resposta: int | None
) -> None:
    """
    Valida o tempo informado para a resposta.
    """

    if (

        tempo_resposta is not None

        and

        tempo_resposta < 0

    ):

        raise ValueError(
            "O tempo de resposta não pode ser negativo."
        )


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

    A pergunta precisa obrigatoriamente fazer
    parte de entrevista_perguntas.

    O snapshot da resposta é copiado diretamente
    do conjunto congelado da entrevista.

    Portanto, mudanças posteriores no cadastro
    original da pergunta não afetam a resposta.

    Retorna o ID da resposta criada.
    """

    # ========================================================
    # VALIDAÇÕES
    # ========================================================

    _validar_id(
        entrevista_id,
        "Entrevista"
    )


    _validar_id(
        pergunta_id,
        "Pergunta"
    )


    texto = _validar_texto_resposta(
        texto_resposta
    )


    _validar_tempo_resposta(
        tempo_resposta
    )


    # ========================================================
    # CONEXÃO
    # ========================================================

    conexao = conectar_banco()

    cursor = conexao.cursor()


    try:

        # ====================================================
        # TRANSAÇÃO
        # ====================================================

        cursor.execute(
            """
            BEGIN IMMEDIATE
            """
        )


        # ====================================================
        # VERIFICAR ENTREVISTA
        # ====================================================

        cursor.execute(
            """
            SELECT

                id,
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


        if (
            entrevista[
                "status"
            ]
            != "em_andamento"
        ):

            raise ValueError(

                "Não é possível registrar respostas "
                "em uma entrevista que não esteja "
                "em andamento."

            )


        # ====================================================
        # VERIFICAR PERGUNTA CONGELADA
        # ====================================================

        cursor.execute(
            """
            SELECT

                id,

                entrevista_id,

                pergunta_id,

                pergunta_texto_aplicado,

                exemplo_esperado_aplicado,

                competencia_id_aplicada,

                competencia_nome_aplicada,

                area_tecnica_id_aplicada,

                area_tecnica_nome_aplicada,

                subarea_tecnica_id_aplicada,

                subarea_tecnica_nome_aplicada,

                peso_pergunta_aplicado,

                usa_star_aplicado,

                ordem_pergunta_aplicada

            FROM entrevista_perguntas

            WHERE
                entrevista_id = ?

              AND
                pergunta_id = ?

            LIMIT 1
            """,
            (
                entrevista_id,
                pergunta_id
            )
        )


        pergunta_aplicada = (
            cursor.fetchone()
        )


        if pergunta_aplicada is None:

            raise ValueError(

                "A pergunta informada não pertence "
                "ao conjunto de perguntas desta entrevista."

            )


        # ====================================================
        # VALIDAR SNAPSHOT
        # ====================================================

        if (
            pergunta_aplicada[
                "pergunta_texto_aplicado"
            ]
            is None
        ):

            raise ValueError(
                "A pergunta da entrevista não possui "
                "snapshot histórico válido."
            )


        if (
            pergunta_aplicada[
                "competencia_id_aplicada"
            ]
            is None
        ):

            raise ValueError(
                "A pergunta da entrevista não possui "
                "competência histórica válida."
            )


        if (
            pergunta_aplicada[
                "competencia_nome_aplicada"
            ]
            is None
        ):

            raise ValueError(
                "A pergunta da entrevista não possui "
                "nome histórico da competência."
            )


        if (
            pergunta_aplicada[
                "peso_pergunta_aplicado"
            ]
            is None
        ):

            raise ValueError(
                "A pergunta da entrevista não possui "
                "peso histórico válido."
            )


        if (
            pergunta_aplicada[
                "usa_star_aplicado"
            ]
            is None
        ):

            raise ValueError(
                "A pergunta da entrevista não possui "
                "configuração histórica do método STAR."
            )


        # ====================================================
        # VERIFICAR RESPOSTA DUPLICADA
        # ====================================================

        cursor.execute(
            """
            SELECT id

            FROM respostas

            WHERE
                entrevista_id = ?

              AND
                pergunta_id = ?

            LIMIT 1
            """,
            (
                entrevista_id,
                pergunta_id
            )
        )


        if (
            cursor.fetchone()
            is not None
        ):

            raise ValueError(

                "Esta pergunta já possui uma resposta "
                "registrada nesta entrevista."

            )


        # ====================================================
        # SALVAR RESPOSTA + SNAPSHOT
        # ====================================================

        try:

            cursor.execute(
                """
                INSERT INTO respostas (

                    entrevista_id,

                    pergunta_id,

                    texto_resposta,

                    tempo_resposta,

                    pergunta_texto_aplicado,

                    exemplo_esperado_aplicado,

                    competencia_id_aplicada,

                    competencia_nome_aplicada,

                    peso_pergunta_aplicado,

                    usa_star_aplicado,

                    ordem_pergunta_aplicada

                )

                VALUES (
                    ?,
                    ?,
                    ?,
                    ?,
                    ?,
                    ?,
                    ?,
                    ?,
                    ?,
                    ?,
                    ?
                )
                """,
                (

                    entrevista_id,

                    pergunta_id,

                    texto,

                    tempo_resposta,

                    pergunta_aplicada[
                        "pergunta_texto_aplicado"
                    ],

                    pergunta_aplicada[
                        "exemplo_esperado_aplicado"
                    ],

                    pergunta_aplicada[
                        "competencia_id_aplicada"
                    ],

                    pergunta_aplicada[
                        "competencia_nome_aplicada"
                    ],

                    pergunta_aplicada[
                        "peso_pergunta_aplicado"
                    ],

                    pergunta_aplicada[
                        "usa_star_aplicado"
                    ],

                    pergunta_aplicada[
                        "ordem_pergunta_aplicada"
                    ]

                )
            )


        except sqlite3.IntegrityError as erro:

            # ------------------------------------------------
            # PROTEÇÃO DE CONCORRÊNCIA
            # ------------------------------------------------
            #
            # Mesmo que duas requisições tentem responder
            # à mesma pergunta praticamente ao mesmo tempo,
            # o UNIQUE(entrevista_id, pergunta_id) do banco
            # permanece como a proteção definitiva.
            # ------------------------------------------------

            mensagem = str(
                erro
            ).lower()


            if (

                "unique constraint failed"
                in mensagem

                and

                "respostas.entrevista_id"
                in mensagem

                and

                "respostas.pergunta_id"
                in mensagem

            ):

                raise ValueError(

                    "Esta pergunta já possui uma resposta "
                    "registrada nesta entrevista."

                ) from erro


            raise


        # ====================================================
        # ID
        # ====================================================

        resposta_id = int(
            cursor.lastrowid
        )


        # ====================================================
        # CONFIRMAR
        # ====================================================

        conexao.commit()


        return resposta_id


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

    _validar_id(
        resposta_id,
        "ID da resposta"
    )


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
    Retorna a resposta de determinada pergunta
    dentro de uma entrevista.
    """

    _validar_id(
        entrevista_id,
        "Entrevista"
    )


    _validar_id(
        pergunta_id,
        "Pergunta"
    )


    conexao = conectar_banco()

    cursor = conexao.cursor()


    try:

        cursor.execute(
            """
            SELECT *

            FROM respostas

            WHERE
                entrevista_id = ?

              AND
                pergunta_id = ?

            LIMIT 1
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
    Recupera uma resposta juntamente com
    o snapshot histórico da pergunta.

    O retorno não depende da tabela perguntas.

    Dessa forma, alterações administrativas
    posteriores não alteram entrevistas antigas.
    """

    _validar_id(
        resposta_id,
        "ID da resposta"
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


        # ====================================================
        # VALIDAR SNAPSHOT
        # ====================================================

        if (
            registro[
                "pergunta_texto_aplicado"
            ]
            is None

            or

            registro[
                "competencia_id_aplicada"
            ]
            is None

            or

            registro[
                "competencia_nome_aplicada"
            ]
            is None

            or

            registro[
                "peso_pergunta_aplicado"
            ]
            is None

            or

            registro[
                "usa_star_aplicado"
            ]
            is None
        ):

            raise ValueError(

                "A resposta não possui snapshot histórico "
                "completo da pergunta."

            )


        # ====================================================
        # RETORNO
        # ====================================================

        return {

            "id":
                registro[
                    "id"
                ],

            "resposta_id":
                registro[
                    "id"
                ],

            "entrevista_id":
                registro[
                    "entrevista_id"
                ],

            "pergunta_id":
                registro[
                    "pergunta_id"
                ],

            "pergunta":
                registro[
                    "pergunta_texto_aplicado"
                ],

            "exemplo_esperado":
                registro[
                    "exemplo_esperado_aplicado"
                ],

            "competencia_id":
                registro[
                    "competencia_id_aplicada"
                ],

            "competencia":
                registro[
                    "competencia_nome_aplicada"
                ],

            "peso_pergunta":
                registro[
                    "peso_pergunta_aplicado"
                ],

            "usa_star":
                bool(
                    registro[
                        "usa_star_aplicado"
                    ]
                ),

            "ordem_pergunta":
                registro[
                    "ordem_pergunta_aplicada"
                ],

            "texto_resposta":
                registro[
                    "texto_resposta"
                ],

            "tempo_resposta":
                registro[
                    "tempo_resposta"
                ],

            "data_resposta":
                registro[
                    "data_resposta"
                ]

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

    _validar_id(
        entrevista_id,
        "Entrevista"
    )


    conexao = conectar_banco()

    cursor = conexao.cursor()


    try:

        cursor.execute(
            """
            SELECT
                r.*

            FROM respostas r

            WHERE
                r.entrevista_id = ?

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

            for registro
            in registros

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

    Somente respostas de entrevistas
    em andamento podem ser alteradas.

    Os snapshots históricos não são modificados.
    """

    _validar_id(
        resposta_id,
        "ID da resposta"
    )


    texto = _validar_texto_resposta(
        novo_texto
    )


    _validar_tempo_resposta(
        tempo_resposta
    )


    conexao = conectar_banco()

    cursor = conexao.cursor()


    try:

        cursor.execute(
            """
            BEGIN IMMEDIATE
            """
        )


        # ====================================================
        # VERIFICAR STATUS
        # ====================================================

        cursor.execute(
            """
            SELECT

                r.id,

                e.status

            FROM respostas r

            INNER JOIN entrevistas e

                ON e.id =
                    r.entrevista_id

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


        if (
            registro[
                "status"
            ]
            != "em_andamento"
        ):

            raise ValueError(

                "A resposta não pode ser alterada porque "
                "a entrevista já foi encerrada."

            )


        # ====================================================
        # ATUALIZAR SOMENTE DADOS EDITÁVEIS
        # ====================================================

        cursor.execute(
            """
            UPDATE respostas

            SET

                texto_resposta = ?,

                tempo_resposta = ?

            WHERE id = ?
            """,
            (
                texto,
                tempo_resposta,
                resposta_id
            )
        )


        alterada = (
            cursor.rowcount > 0
        )


        conexao.commit()


        return alterada


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

    Somente respostas de entrevistas
    em andamento podem ser excluídas.

    O conjunto congelado de perguntas
    não é alterado.
    """

    _validar_id(
        resposta_id,
        "ID da resposta"
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

                r.id,

                e.status

            FROM respostas r

            INNER JOIN entrevistas e

                ON e.id =
                    r.entrevista_id

            WHERE r.id = ?
            """,
            (
                resposta_id,
            )
        )


        registro = cursor.fetchone()


        if registro is None:

            conexao.rollback()

            return False


        if (
            registro[
                "status"
            ]
            != "em_andamento"
        ):

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


        excluida = (
            cursor.rowcount > 0
        )


        conexao.commit()


        return excluida


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
    Verifica se uma pergunta já possui
    resposta dentro da entrevista.
    """

    _validar_id(
        entrevista_id,
        "Entrevista"
    )


    _validar_id(
        pergunta_id,
        "Pergunta"
    )


    conexao = conectar_banco()

    cursor = conexao.cursor()


    try:

        cursor.execute(
            """
            SELECT 1

            FROM respostas

            WHERE
                entrevista_id = ?

              AND
                pergunta_id = ?

            LIMIT 1
            """,
            (
                entrevista_id,
                pergunta_id
            )
        )


        return (
            cursor.fetchone()
            is not None
        )


    finally:

        conexao.close()


# ============================================================
# CONTAR RESPOSTAS
# ============================================================

def contar_respostas_entrevista(
    entrevista_id: int
) -> int:
    """
    Retorna a quantidade de respostas
    existentes em uma entrevista.
    """

    _validar_id(
        entrevista_id,
        "Entrevista"
    )


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
            registro[
                "quantidade"
            ]
        )


    finally:

        conexao.close()


# ============================================================
# CONTAR RESPOSTAS PENDENTES
# ============================================================

def contar_respostas_pendentes(
    entrevista_id: int
) -> int:
    """
    Retorna quantas perguntas congeladas ainda
    não possuem resposta.

    Esta função poderá ser utilizada pelo
    frontend para mostrar o progresso.
    """

    _validar_id(
        entrevista_id,
        "Entrevista"
    )


    conexao = conectar_banco()

    cursor = conexao.cursor()


    try:

        cursor.execute(
            """
            SELECT COUNT(*) AS quantidade

            FROM entrevista_perguntas ep

            WHERE
                ep.entrevista_id = ?

              AND NOT EXISTS (

                    SELECT 1

                    FROM respostas r

                    WHERE
                        r.entrevista_id =
                            ep.entrevista_id

                      AND
                        r.pergunta_id =
                            ep.pergunta_id

              )
            """,
            (
                entrevista_id,
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
# CONVERTER REGISTRO
# ============================================================

def _registro_para_resposta(
    registro: sqlite3.Row
) -> Resposta:
    """
    Converte um registro SQLite
    em objeto Resposta.

    Também carrega os snapshots históricos
    armazenados na própria resposta.
    """

    colunas = registro.keys()


    return Resposta(

        id=registro[
            "id"
        ],

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
        ],

        pergunta_texto_aplicado=(

            registro[
                "pergunta_texto_aplicado"
            ]

            if (
                "pergunta_texto_aplicado"
                in colunas
            )

            else None
        ),

        exemplo_esperado_aplicado=(

            registro[
                "exemplo_esperado_aplicado"
            ]

            if (
                "exemplo_esperado_aplicado"
                in colunas
            )

            else None
        ),

        competencia_id_aplicada=(

            registro[
                "competencia_id_aplicada"
            ]

            if (
                "competencia_id_aplicada"
                in colunas
            )

            else None
        ),

        competencia_nome_aplicada=(

            registro[
                "competencia_nome_aplicada"
            ]

            if (
                "competencia_nome_aplicada"
                in colunas
            )

            else None
        ),

        peso_pergunta_aplicado=(

            registro[
                "peso_pergunta_aplicado"
            ]

            if (
                "peso_pergunta_aplicado"
                in colunas
            )

            else None
        ),

        usa_star_aplicado=(

            bool(
                registro[
                    "usa_star_aplicado"
                ]
            )

            if (
                "usa_star_aplicado"
                in colunas

                and

                registro[
                    "usa_star_aplicado"
                ]
                is not None
            )

            else None
        ),

        ordem_pergunta_aplicada=(

            registro[
                "ordem_pergunta_aplicada"
            ]

            if (
                "ordem_pergunta_aplicada"
                in colunas
            )

            else None
        )

    )