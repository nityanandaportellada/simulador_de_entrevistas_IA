"""
perguntas.py

Módulo responsável pelo gerenciamento das perguntas
do Simulador de Entrevistas.

Versão: 0.2

Responsabilidades:

- cadastrar perguntas;
- listar perguntas;
- buscar pergunta por ID;
- editar perguntas;
- ativar perguntas;
- desativar perguntas;
- excluir perguntas quando permitido;
- filtrar perguntas por tipo de entrevista;
- filtrar perguntas por competência;
- validar integridade entre:
    tipo de entrevista;
    competência;
    pergunta.

REGRAS DE INTEGRIDADE:

1. Uma nova pergunta somente pode utilizar
   um tipo de entrevista existente e ativo.

2. Uma nova pergunta somente pode utilizar
   uma competência existente e ativa.

3. Uma pergunta não pode ser reativada caso
   o tipo de entrevista esteja inativo.

4. Uma pergunta não pode ser reativada caso
   a competência esteja inativa.

5. Ao listar somente perguntas ativas,
   também são considerados os estados do
   tipo de entrevista e da competência.

6. Perguntas já utilizadas em entrevistas
   não podem ser excluídas fisicamente.

O acesso ao banco de dados é realizado através
do módulo database.py.
"""

import sqlite3


try:

    from .database import conectar_banco

    from .models import Pergunta

except ImportError:

    from database import conectar_banco

    from models import Pergunta


# ============================================================
# VALIDAR ID DA PERGUNTA
# ============================================================

def _validar_pergunta_id(
    pergunta_id: int
) -> None:
    """
    Valida o ID de uma pergunta.
    """

    if not isinstance(
        pergunta_id,
        int
    ):

        raise ValueError(
            "O ID da pergunta deve ser um número inteiro."
        )


    if pergunta_id <= 0:

        raise ValueError(
            "O ID da pergunta deve ser maior que zero."
        )


# ============================================================
# VALIDAR TIPO DE ENTREVISTA
# ============================================================

def _validar_tipo_entrevista_ativo(
    tipo_entrevista_id: int
) -> None:
    """
    Verifica se o tipo de entrevista existe
    e está ativo.
    """

    if not isinstance(
        tipo_entrevista_id,
        int
    ):

        raise ValueError(
            "O tipo de entrevista informado é inválido."
        )


    if tipo_entrevista_id <= 0:

        raise ValueError(
            "O tipo de entrevista informado é inválido."
        )


    conexao = conectar_banco()

    cursor = conexao.cursor()


    try:

        cursor.execute(
            """
            SELECT
                id,
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

            raise ValueError(
                "O tipo de entrevista informado "
                "não foi encontrado."
            )


        if not bool(
            registro["ativo"]
        ):

            raise ValueError(
                "O tipo de entrevista informado está inativo."
            )


    finally:

        conexao.close()


# ============================================================
# VALIDAR COMPETÊNCIA
# ============================================================

def _validar_competencia_ativa(
    competencia_id: int
) -> None:
    """
    Verifica se a competência existe
    e está ativa.

    IMPORTANTE:

    Na tabela competencias, o campo de status
    se chama 'ativa'.
    """

    if not isinstance(
        competencia_id,
        int
    ):

        raise ValueError(
            "A competência informada é inválida."
        )


    if competencia_id <= 0:

        raise ValueError(
            "A competência informada é inválida."
        )


    conexao = conectar_banco()

    cursor = conexao.cursor()


    try:

        cursor.execute(
            """
            SELECT
                id,
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

            raise ValueError(
                "A competência informada não foi encontrada."
            )


        if not bool(
            registro["ativa"]
        ):

            raise ValueError(
                "A competência informada está inativa."
            )


    finally:

        conexao.close()


# ============================================================
# CADASTRAR PERGUNTA
# ============================================================

def cadastrar_pergunta(
    pergunta: Pergunta
) -> int:
    """
    Cadastra uma nova pergunta no banco de dados.

    O tipo de entrevista e a competência
    precisam existir e estar ativos.

    Retorna o ID da pergunta cadastrada.
    """

    validar_pergunta(
        pergunta
    )


    conexao = conectar_banco()

    cursor = conexao.cursor()


    try:

        cursor.execute(
            """
            INSERT INTO perguntas (
                tipo_entrevista_id,
                competencia_id,
                texto,
                exemplo_esperado,
                ordem,
                ativa,
                peso,
                usa_star
            )

            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                pergunta.tipo_entrevista_id,

                pergunta.competencia_id,

                pergunta.texto.strip(),

                (
                    pergunta.exemplo_esperado.strip()
                    if (
                        pergunta.exemplo_esperado
                        and pergunta.exemplo_esperado.strip()
                    )
                    else None
                ),

                pergunta.ordem,

                1
                if pergunta.ativa
                else 0,

                pergunta.peso,

                1
                if pergunta.usa_star
                else 0
            )
        )


        pergunta_id = (
            cursor.lastrowid
        )


        conexao.commit()


        return pergunta_id


    except sqlite3.Error:

        conexao.rollback()

        raise


    finally:

        conexao.close()


# ============================================================
# LISTAR TODAS AS PERGUNTAS
# ============================================================

def listar_perguntas(
    somente_ativas: bool = False
) -> list[Pergunta]:
    """
    Retorna as perguntas cadastradas.

    Quando somente_ativas=True, uma pergunta
    somente será considerada disponível quando:

    - a própria pergunta estiver ativa;
    - o tipo de entrevista estiver ativo;
    - a competência estiver ativa.
    """

    conexao = conectar_banco()

    cursor = conexao.cursor()


    try:

        if somente_ativas:

            cursor.execute(
                """
                SELECT
                    p.*

                FROM perguntas p

                INNER JOIN tipos_entrevista t
                    ON t.id = p.tipo_entrevista_id

                INNER JOIN competencias c
                    ON c.id = p.competencia_id

                WHERE p.ativa = 1

                  AND t.ativo = 1

                  AND c.ativa = 1

                ORDER BY
                    COALESCE(
                        p.ordem,
                        999999
                    ),
                    p.id
                """
            )


        else:

            cursor.execute(
                """
                SELECT *

                FROM perguntas

                ORDER BY
                    COALESCE(
                        ordem,
                        999999
                    ),
                    id
                """
            )


        registros = (
            cursor.fetchall()
        )


        return [

            _registro_para_pergunta(
                registro
            )

            for registro in registros
        ]


    finally:

        conexao.close()


# ============================================================
# BUSCAR PERGUNTA POR ID
# ============================================================

def buscar_pergunta(
    pergunta_id: int
) -> Pergunta | None:
    """
    Busca uma pergunta pelo seu ID.

    Retorna um objeto Pergunta caso seja encontrada.

    Caso contrário, retorna None.
    """

    _validar_pergunta_id(
        pergunta_id
    )


    conexao = conectar_banco()

    cursor = conexao.cursor()


    try:

        cursor.execute(
            """
            SELECT *

            FROM perguntas

            WHERE id = ?
            """,
            (
                pergunta_id,
            )
        )


        registro = (
            cursor.fetchone()
        )


        if registro is None:

            return None


        return _registro_para_pergunta(
            registro
        )


    finally:

        conexao.close()


# ============================================================
# LISTAR PERGUNTAS POR TIPO DE ENTREVISTA
# ============================================================

def listar_perguntas_por_tipo(
    tipo_entrevista_id: int,
    somente_ativas: bool = True
) -> list[Pergunta]:
    """
    Retorna as perguntas associadas a determinado
    tipo de entrevista.

    Quando somente_ativas=True, também verifica
    o status do tipo e da competência.
    """

    if not isinstance(
        tipo_entrevista_id,
        int
    ):

        raise ValueError(
            "O tipo de entrevista informado é inválido."
        )


    if tipo_entrevista_id <= 0:

        raise ValueError(
            "O tipo de entrevista informado é inválido."
        )


    conexao = conectar_banco()

    cursor = conexao.cursor()


    try:

        if somente_ativas:

            cursor.execute(
                """
                SELECT
                    p.*

                FROM perguntas p

                INNER JOIN tipos_entrevista t
                    ON t.id = p.tipo_entrevista_id

                INNER JOIN competencias c
                    ON c.id = p.competencia_id

                WHERE p.tipo_entrevista_id = ?

                  AND p.ativa = 1

                  AND t.ativo = 1

                  AND c.ativa = 1

                ORDER BY
                    COALESCE(
                        p.ordem,
                        999999
                    ),
                    p.id
                """,
                (
                    tipo_entrevista_id,
                )
            )


        else:

            cursor.execute(
                """
                SELECT *

                FROM perguntas

                WHERE tipo_entrevista_id = ?

                ORDER BY
                    COALESCE(
                        ordem,
                        999999
                    ),
                    id
                """,
                (
                    tipo_entrevista_id,
                )
            )


        registros = (
            cursor.fetchall()
        )


        return [

            _registro_para_pergunta(
                registro
            )

            for registro in registros
        ]


    finally:

        conexao.close()


# ============================================================
# LISTAR PERGUNTAS POR COMPETÊNCIA
# ============================================================

def listar_perguntas_por_competencia(
    competencia_id: int,
    somente_ativas: bool = True
) -> list[Pergunta]:
    """
    Retorna perguntas associadas a determinada competência.

    Quando somente_ativas=True, também verifica
    o status da competência e do tipo de entrevista.
    """

    if not isinstance(
        competencia_id,
        int
    ):

        raise ValueError(
            "A competência informada é inválida."
        )


    if competencia_id <= 0:

        raise ValueError(
            "A competência informada é inválida."
        )


    conexao = conectar_banco()

    cursor = conexao.cursor()


    try:

        if somente_ativas:

            cursor.execute(
                """
                SELECT
                    p.*

                FROM perguntas p

                INNER JOIN tipos_entrevista t
                    ON t.id = p.tipo_entrevista_id

                INNER JOIN competencias c
                    ON c.id = p.competencia_id

                WHERE p.competencia_id = ?

                  AND p.ativa = 1

                  AND t.ativo = 1

                  AND c.ativa = 1

                ORDER BY
                    COALESCE(
                        p.ordem,
                        999999
                    ),
                    p.id
                """,
                (
                    competencia_id,
                )
            )


        else:

            cursor.execute(
                """
                SELECT *

                FROM perguntas

                WHERE competencia_id = ?

                ORDER BY
                    COALESCE(
                        ordem,
                        999999
                    ),
                    id
                """,
                (
                    competencia_id,
                )
            )


        registros = (
            cursor.fetchall()
        )


        return [

            _registro_para_pergunta(
                registro
            )

            for registro in registros
        ]


    finally:

        conexao.close()


# ============================================================
# EDITAR PERGUNTA
# ============================================================

def editar_pergunta(
    pergunta_id: int,
    pergunta: Pergunta
) -> bool:
    """
    Atualiza uma pergunta existente.

    O tipo de entrevista e a competência escolhidos
    precisam existir e estar ativos.

    Retorna True quando a pergunta for atualizada.

    Retorna False caso o ID não exista.
    """

    _validar_pergunta_id(
        pergunta_id
    )


    pergunta_existente = buscar_pergunta(
        pergunta_id
    )


    if pergunta_existente is None:

        return False


    validar_pergunta(
        pergunta
    )


    conexao = conectar_banco()

    cursor = conexao.cursor()


    try:

        cursor.execute(
            """
            UPDATE perguntas

            SET
                tipo_entrevista_id = ?,
                competencia_id = ?,
                texto = ?,
                exemplo_esperado = ?,
                ordem = ?,
                ativa = ?,
                peso = ?,
                usa_star = ?

            WHERE id = ?
            """,
            (
                pergunta.tipo_entrevista_id,

                pergunta.competencia_id,

                pergunta.texto.strip(),

                (
                    pergunta.exemplo_esperado.strip()
                    if (
                        pergunta.exemplo_esperado
                        and pergunta.exemplo_esperado.strip()
                    )
                    else None
                ),

                pergunta.ordem,

                1
                if pergunta.ativa
                else 0,

                pergunta.peso,

                1
                if pergunta.usa_star
                else 0,

                pergunta_id
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
# DESATIVAR PERGUNTA
# ============================================================

def desativar_pergunta(
    pergunta_id: int
) -> bool:
    """
    Desativa uma pergunta.

    A pergunta permanece no banco para preservar
    o histórico das entrevistas anteriores.
    """

    return _alterar_status_pergunta(
        pergunta_id,
        False
    )


# ============================================================
# REATIVAR PERGUNTA
# ============================================================

def reativar_pergunta(
    pergunta_id: int
) -> bool:
    """
    Reativa uma pergunta anteriormente desativada.

    Para ser reativada:

    - o tipo de entrevista deve estar ativo;
    - a competência deve estar ativa.
    """

    _validar_pergunta_id(
        pergunta_id
    )


    pergunta = buscar_pergunta(
        pergunta_id
    )


    if pergunta is None:

        return False


    _validar_tipo_entrevista_ativo(
        pergunta.tipo_entrevista_id
    )


    _validar_competencia_ativa(
        pergunta.competencia_id
    )


    return _alterar_status_pergunta(
        pergunta_id,
        True
    )


# ============================================================
# ALTERAR STATUS DA PERGUNTA
# ============================================================

def _alterar_status_pergunta(
    pergunta_id: int,
    ativa: bool
) -> bool:
    """
    Função interna utilizada para ativar ou
    desativar perguntas.
    """

    _validar_pergunta_id(
        pergunta_id
    )


    conexao = conectar_banco()

    cursor = conexao.cursor()


    try:

        cursor.execute(
            """
            SELECT id

            FROM perguntas

            WHERE id = ?
            """,
            (
                pergunta_id,
            )
        )


        if cursor.fetchone() is None:

            return False


        cursor.execute(
            """
            UPDATE perguntas

            SET ativa = ?

            WHERE id = ?
            """,
            (
                1
                if ativa
                else 0,

                pergunta_id
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
# EXCLUIR PERGUNTA
# ============================================================

def excluir_pergunta(
    pergunta_id: int
) -> bool:
    """
    Exclui fisicamente uma pergunta.

    IMPORTANTE:

    Perguntas utilizadas em entrevistas anteriores
    não podem ser excluídas.

    Nesses casos, deve-se utilizar
    desativar_pergunta().
    """

    _validar_pergunta_id(
        pergunta_id
    )


    conexao = conectar_banco()

    cursor = conexao.cursor()


    try:

        # ----------------------------------------------------
        # VERIFICAR EXISTÊNCIA
        # ----------------------------------------------------

        cursor.execute(
            """
            SELECT id

            FROM perguntas

            WHERE id = ?
            """,
            (
                pergunta_id,
            )
        )


        if cursor.fetchone() is None:

            return False


        # ----------------------------------------------------
        # VERIFICAR USO
        # ----------------------------------------------------

        cursor.execute(
            """
            SELECT
                COUNT(*) AS quantidade

            FROM respostas

            WHERE pergunta_id = ?
            """,
            (
                pergunta_id,
            )
        )


        registro = (
            cursor.fetchone()
        )


        quantidade_respostas = int(
            registro["quantidade"]
        )


        if quantidade_respostas > 0:

            raise ValueError(
                "A pergunta não pode ser excluída porque "
                "já foi utilizada em uma entrevista. "
                "Utilize a opção de desativação."
            )


        # ----------------------------------------------------
        # EXCLUIR
        # ----------------------------------------------------

        cursor.execute(
            """
            DELETE FROM perguntas

            WHERE id = ?
            """,
            (
                pergunta_id,
            )
        )


        conexao.commit()


        return (
            cursor.rowcount > 0
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
# VALIDAR PERGUNTA
# ============================================================

def validar_pergunta(
    pergunta: Pergunta
) -> None:
    """
    Valida os dados de uma pergunta.

    Caso alguma regra não seja atendida,
    gera ValueError.

    Além da validação dos campos, esta função
    também verifica a integridade das referências.
    """

    if pergunta is None:

        raise ValueError(
            "A pergunta é obrigatória."
        )


    # --------------------------------------------------------
    # TEXTO
    # --------------------------------------------------------

    if not pergunta.texto:

        raise ValueError(
            "O texto da pergunta é obrigatório."
        )


    if not isinstance(
        pergunta.texto,
        str
    ):

        raise ValueError(
            "O texto da pergunta deve ser um texto."
        )


    if not pergunta.texto.strip():

        raise ValueError(
            "O texto da pergunta não pode estar vazio."
        )


    # --------------------------------------------------------
    # TIPO DE ENTREVISTA
    # --------------------------------------------------------

    if pergunta.tipo_entrevista_id is None:

        raise ValueError(
            "O tipo de entrevista é obrigatório."
        )


    _validar_tipo_entrevista_ativo(
        pergunta.tipo_entrevista_id
    )


    # --------------------------------------------------------
    # COMPETÊNCIA
    # --------------------------------------------------------

    if pergunta.competencia_id is None:

        raise ValueError(
            "A competência é obrigatória."
        )


    _validar_competencia_ativa(
        pergunta.competencia_id
    )


    # --------------------------------------------------------
    # PESO
    # --------------------------------------------------------

    if pergunta.peso is None:

        raise ValueError(
            "O peso da pergunta é obrigatório."
        )


    try:

        peso = float(
            pergunta.peso
        )

    except (
        TypeError,
        ValueError
    ):

        raise ValueError(
            "O peso da pergunta deve ser numérico."
        )


    if peso <= 0:

        raise ValueError(
            "O peso da pergunta deve ser maior que zero."
        )


    # --------------------------------------------------------
    # ORDEM
    # --------------------------------------------------------

    if pergunta.ordem is not None:

        if not isinstance(
            pergunta.ordem,
            int
        ):

            raise ValueError(
                "A ordem da pergunta deve ser "
                "um número inteiro."
            )


        if pergunta.ordem <= 0:

            raise ValueError(
                "A ordem da pergunta deve ser maior que zero."
            )


    # --------------------------------------------------------
    # EXEMPLO ESPERADO
    # --------------------------------------------------------

    if (
        pergunta.exemplo_esperado is not None
        and not isinstance(
            pergunta.exemplo_esperado,
            str
        )
    ):

        raise ValueError(
            "O exemplo esperado deve ser um texto."
        )


# ============================================================
# CONVERTER REGISTRO SQLITE PARA PERGUNTA
# ============================================================

def _registro_para_pergunta(
    registro: sqlite3.Row
) -> Pergunta:
    """
    Converte um registro retornado pelo SQLite
    em um objeto da classe Pergunta.
    """

    return Pergunta(

        id=registro[
            "id"
        ],

        tipo_entrevista_id=registro[
            "tipo_entrevista_id"
        ],

        competencia_id=registro[
            "competencia_id"
        ],

        texto=registro[
            "texto"
        ],

        exemplo_esperado=registro[
            "exemplo_esperado"
        ],

        ordem=registro[
            "ordem"
        ],

        ativa=bool(
            registro[
                "ativa"
            ]
        ),

        peso=registro[
            "peso"
        ],

        usa_star=bool(
            registro[
                "usa_star"
            ]
        ),

        data_criacao=registro[
            "data_criacao"
        ]

    )