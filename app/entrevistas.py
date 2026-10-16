"""
entrevistas.py

Módulo responsável pelo gerenciamento das entrevistas
do Simulador de Entrevistas.

Responsabilidades:

- criar entrevistas;
- receber área e subárea para entrevistas técnicas;
- validar área e subárea;
- congelar o conjunto de perguntas no início da entrevista;
- preservar snapshots históricos;
- buscar entrevistas;
- listar entrevistas de um usuário;
- listar perguntas congeladas de uma entrevista;
- alterar status;
- finalizar entrevistas;
- cancelar entrevistas;
- registrar pontuação final;
- consultar quantidade de respostas;
- consultar quantidade de perguntas da entrevista.

Regras para entrevistas técnicas:

- tipos com usa_area_tecnica = 1 exigem área;
- tipos com usa_area_tecnica = 1 exigem subárea;
- área e subárea precisam estar ativas;
- a subárea precisa pertencer à área;
- quando uma subárea específica é escolhida,
  são utilizadas perguntas da subárea Geral
  e da subárea selecionada;
- quando Geral é escolhida, são utilizadas
  apenas perguntas da subárea Geral.

As perguntas são congeladas na tabela
entrevista_perguntas no momento da criação
da entrevista.

Isso impede que alterações administrativas
posteriores modifiquem entrevistas que já começaram.

O módulo não realiza a análise por Inteligência Artificial.
Essa responsabilidade continua no módulo analise.py.
"""

import sqlite3

from datetime import (
    datetime,
    timezone
)


try:

    from .database import conectar_banco

    from .models import (
        Entrevista,
        EntrevistaPergunta
    )


except ImportError:

    from database import conectar_banco

    from models import (
        Entrevista,
        EntrevistaPergunta
    )


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
# DATA/HORA ATUAL
# ============================================================

def _agora_utc() -> str:
    """
    Retorna data e hora atual em UTC
    no formato utilizado pelo banco.
    """

    return datetime.now(
        timezone.utc
    ).strftime(
        "%Y-%m-%d %H:%M:%S"
    )


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
# BUSCAR USUÁRIO
# ============================================================

def _buscar_usuario_ativo(
    cursor: sqlite3.Cursor,
    usuario_id: int
):
    """
    Busca um usuário ativo utilizando
    a conexão da transação atual.
    """

    cursor.execute(
        """
        SELECT

            id,
            nome,
            email,
            perfil,
            ativo

        FROM usuarios

        WHERE
            id = ?

          AND
            ativo = 1
        """,
        (
            usuario_id,
        )
    )


    return cursor.fetchone()


# ============================================================
# BUSCAR TIPO DE ENTREVISTA
# ============================================================

def _buscar_tipo_entrevista_ativo(
    cursor: sqlite3.Cursor,
    tipo_entrevista_id: int
):
    """
    Busca um tipo de entrevista ativo.

    Também retorna usa_area_tecnica.
    """

    cursor.execute(
        """
        SELECT

            id,
            nome,
            descricao,
            ativo,
            usa_area_tecnica

        FROM tipos_entrevista

        WHERE
            id = ?

          AND
            ativo = 1
        """,
        (
            tipo_entrevista_id,
        )
    )


    return cursor.fetchone()


# ============================================================
# BUSCAR ÁREA TÉCNICA
# ============================================================

def _buscar_area_tecnica_ativa(
    cursor: sqlite3.Cursor,
    area_tecnica_id: int
):
    """
    Busca uma área técnica ativa.
    """

    cursor.execute(
        """
        SELECT

            id,
            nome,
            descricao,
            ativo,
            ordem

        FROM areas_tecnicas

        WHERE
            id = ?

          AND
            ativo = 1
        """,
        (
            area_tecnica_id,
        )
    )


    return cursor.fetchone()


# ============================================================
# BUSCAR SUBÁREA TÉCNICA
# ============================================================

def _buscar_subarea_tecnica_ativa(
    cursor: sqlite3.Cursor,
    subarea_tecnica_id: int
):
    """
    Busca uma subárea técnica ativa.
    """

    cursor.execute(
        """
        SELECT

            id,
            area_tecnica_id,
            nome,
            descricao,
            eh_geral,
            ativo,
            ordem

        FROM subareas_tecnicas

        WHERE
            id = ?

          AND
            ativo = 1
        """,
        (
            subarea_tecnica_id,
        )
    )


    return cursor.fetchone()


# ============================================================
# BUSCAR SUBÁREA GERAL
# ============================================================

def _buscar_subarea_geral(
    cursor: sqlite3.Cursor,
    area_tecnica_id: int
):
    """
    Busca a subárea Geral ativa
    pertencente à área informada.
    """

    cursor.execute(
        """
        SELECT

            id,
            area_tecnica_id,
            nome,
            descricao,
            eh_geral,
            ativo,
            ordem

        FROM subareas_tecnicas

        WHERE
            area_tecnica_id = ?

          AND
            eh_geral = 1

          AND
            ativo = 1

        LIMIT 1
        """,
        (
            area_tecnica_id,
        )
    )


    return cursor.fetchone()


# ============================================================
# VALIDAR ÁREA E SUBÁREA
# ============================================================

def _validar_contexto_area_tecnica(
    cursor: sqlite3.Cursor,
    tipo,
    area_tecnica_id: int | None,
    subarea_tecnica_id: int | None
):
    """
    Valida área e subárea conforme a configuração
    do tipo de entrevista.

    Retorna:

    (
        area,
        subarea,
        subarea_geral
    )

    Para tipos que não utilizam área,
    retorna:

    (
        None,
        None,
        None
    )
    """

    usa_area_tecnica = bool(
        tipo[
            "usa_area_tecnica"
        ]
    )


    # ========================================================
    # TIPO NÃO UTILIZA ÁREA TÉCNICA
    # ========================================================

    if not usa_area_tecnica:

        if (
            area_tecnica_id is not None
            or
            subarea_tecnica_id is not None
        ):

            raise ValueError(
                "Este tipo de entrevista não utiliza "
                "área ou subárea técnica."
            )


        return (
            None,
            None,
            None
        )


    # ========================================================
    # TIPO UTILIZA ÁREA TÉCNICA
    # ========================================================

    if area_tecnica_id is None:

        raise ValueError(
            "A área técnica é obrigatória "
            "para este tipo de entrevista."
        )


    if subarea_tecnica_id is None:

        raise ValueError(
            "A subárea técnica é obrigatória "
            "para este tipo de entrevista."
        )


    _validar_id(
        area_tecnica_id,
        "Área técnica"
    )


    _validar_id(
        subarea_tecnica_id,
        "Subárea técnica"
    )


    # --------------------------------------------------------
    # ÁREA
    # --------------------------------------------------------

    area = _buscar_area_tecnica_ativa(

        cursor,

        area_tecnica_id

    )


    if area is None:

        raise ValueError(
            "Área técnica não encontrada "
            "ou inativa."
        )


    # --------------------------------------------------------
    # SUBÁREA
    # --------------------------------------------------------

    subarea = _buscar_subarea_tecnica_ativa(

        cursor,

        subarea_tecnica_id

    )


    if subarea is None:

        raise ValueError(
            "Subárea técnica não encontrada "
            "ou inativa."
        )


    # --------------------------------------------------------
    # SUBÁREA PRECISA PERTENCER À ÁREA
    # --------------------------------------------------------

    if (
        subarea[
            "area_tecnica_id"
        ]
        != area_tecnica_id
    ):

        raise ValueError(
            "A subárea informada não pertence "
            "à área técnica selecionada."
        )


    # --------------------------------------------------------
    # LOCALIZAR GERAL
    # --------------------------------------------------------

    subarea_geral = _buscar_subarea_geral(

        cursor,

        area_tecnica_id

    )


    if subarea_geral is None:

        raise ValueError(
            "A área técnica selecionada não possui "
            "uma subárea Geral ativa."
        )


    return (
        area,
        subarea,
        subarea_geral
    )


# ============================================================
# BUSCAR PERGUNTAS NÃO TÉCNICAS
# ============================================================

def _buscar_perguntas_tipo_normal(
    cursor: sqlite3.Cursor,
    tipo_entrevista_id: int
):
    """
    Busca perguntas disponíveis para um tipo
    que não utiliza área técnica.

    São consideradas apenas perguntas:

    - ativas;
    - pertencentes ao tipo informado;
    - com competência ativa;
    - sem área;
    - sem subárea.
    """

    cursor.execute(
        """
        SELECT

            p.id,

            p.tipo_entrevista_id,

            p.competencia_id,

            p.texto,

            p.exemplo_esperado,

            p.ordem,

            p.peso,

            p.usa_star,

            c.nome
                AS competencia_nome

        FROM perguntas p

        INNER JOIN competencias c

            ON c.id =
                p.competencia_id

        WHERE
            p.tipo_entrevista_id = ?

          AND
            p.ativa = 1

          AND
            c.ativa = 1

          AND
            p.area_tecnica_id IS NULL

          AND
            p.subarea_tecnica_id IS NULL

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


    return cursor.fetchall()


# ============================================================
# BUSCAR PERGUNTAS TÉCNICAS
# ============================================================

def _buscar_perguntas_tipo_tecnico(
    cursor: sqlite3.Cursor,
    tipo_entrevista_id: int,
    area_tecnica_id: int,
    subarea_tecnica_id: int,
    subarea_geral_id: int
):
    """
    Busca perguntas para uma entrevista técnica.

    Regra:

    Se uma subárea específica for selecionada:

        Geral
        +
        subárea específica

    Se Geral for selecionada:

        apenas Geral
    """

    # --------------------------------------------------------
    # DEFINIR SUBÁREAS DA ENTREVISTA
    # --------------------------------------------------------

    if (
        subarea_tecnica_id
        == subarea_geral_id
    ):

        subareas_ids = [
            subarea_geral_id
        ]


    else:

        subareas_ids = [

            subarea_geral_id,

            subarea_tecnica_id

        ]


    placeholders = ",".join(
        "?"
        for _ in subareas_ids
    )


    parametros = [

        tipo_entrevista_id,

        area_tecnica_id,

        *subareas_ids

    ]


    # --------------------------------------------------------
    # CONSULTAR PERGUNTAS
    # --------------------------------------------------------

    cursor.execute(
        f"""
        SELECT

            p.id,

            p.tipo_entrevista_id,

            p.competencia_id,

            p.texto,

            p.exemplo_esperado,

            p.ordem,

            p.peso,

            p.usa_star,

            p.area_tecnica_id,

            p.subarea_tecnica_id,


            c.nome
                AS competencia_nome,


            a.nome
                AS area_tecnica_nome,


            s.nome
                AS subarea_tecnica_nome,


            s.eh_geral
                AS subarea_eh_geral

        FROM perguntas p


        INNER JOIN competencias c

            ON c.id =
                p.competencia_id


        INNER JOIN areas_tecnicas a

            ON a.id =
                p.area_tecnica_id


        INNER JOIN subareas_tecnicas s

            ON s.id =
                p.subarea_tecnica_id


        WHERE
            p.tipo_entrevista_id = ?

          AND
            p.ativa = 1

          AND
            c.ativa = 1

          AND
            a.ativo = 1

          AND
            s.ativo = 1

          AND
            p.area_tecnica_id = ?

          AND
            p.subarea_tecnica_id IN (
                {placeholders}
            )

          AND
            s.area_tecnica_id =
                p.area_tecnica_id


        ORDER BY

            CASE

                WHEN s.eh_geral = 1

                THEN 0

                ELSE 1

            END,

            COALESCE(
                p.ordem,
                999999
            ),

            p.id
        """,
        tuple(
            parametros
        )
    )


    return cursor.fetchall()


# ============================================================
# CONGELAR PERGUNTAS
# ============================================================

def _congelar_perguntas(
    cursor: sqlite3.Cursor,
    entrevista_id: int,
    perguntas
) -> None:
    """
    Copia as perguntas selecionadas para
    entrevista_perguntas.

    Depois disso, a entrevista não depende mais
    diretamente do cadastro atual da pergunta.

    Mesmo que o administrador edite:

    - texto;
    - competência;
    - peso;
    - método STAR;
    - ordem;
    - área;
    - subárea;

    a entrevista continuará utilizando o snapshot.
    """

    for pergunta in perguntas:

        # ----------------------------------------------------
        # COLUNAS DISPONÍVEIS
        # ----------------------------------------------------

        colunas = pergunta.keys()


        # ----------------------------------------------------
        # ÁREA
        # ----------------------------------------------------

        area_tecnica_id_aplicada = (

            pergunta[
                "area_tecnica_id"
            ]

            if (
                "area_tecnica_id"
                in colunas
            )

            else None

        )


        area_tecnica_nome_aplicada = (

            pergunta[
                "area_tecnica_nome"
            ]

            if (
                "area_tecnica_nome"
                in colunas
            )

            else None

        )


        # ----------------------------------------------------
        # SUBÁREA
        # ----------------------------------------------------

        subarea_tecnica_id_aplicada = (

            pergunta[
                "subarea_tecnica_id"
            ]

            if (
                "subarea_tecnica_id"
                in colunas
            )

            else None

        )


        subarea_tecnica_nome_aplicada = (

            pergunta[
                "subarea_tecnica_nome"
            ]

            if (
                "subarea_tecnica_nome"
                in colunas
            )

            else None

        )


        # ----------------------------------------------------
        # SALVAR SNAPSHOT
        # ----------------------------------------------------

        cursor.execute(
            """
            INSERT INTO entrevista_perguntas (

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
                ?,
                ?,
                ?
            )
            """,
            (

                entrevista_id,

                pergunta[
                    "id"
                ],

                pergunta[
                    "texto"
                ],

                pergunta[
                    "exemplo_esperado"
                ],

                pergunta[
                    "competencia_id"
                ],

                pergunta[
                    "competencia_nome"
                ],

                area_tecnica_id_aplicada,

                area_tecnica_nome_aplicada,

                subarea_tecnica_id_aplicada,

                subarea_tecnica_nome_aplicada,

                pergunta[
                    "peso"
                ],

                (
                    1
                    if bool(
                        pergunta[
                            "usa_star"
                        ]
                    )
                    else 0
                ),

                pergunta[
                    "ordem"
                ]

            )
        )


# ============================================================
# CRIAR ENTREVISTA
# ============================================================

def criar_entrevista(
    usuario_id: int,
    tipo_entrevista_id: int,
    area_tecnica_id: int | None = None,
    subarea_tecnica_id: int | None = None
) -> int:
    """
    Cria uma nova entrevista.

    A entrevista inicia com status:

        em_andamento

    Para tipos que não usam área:

        area_tecnica_id = None
        subarea_tecnica_id = None

    Para tipos que usam área:

        area_tecnica_id = obrigatório
        subarea_tecnica_id = obrigatório

    As perguntas são selecionadas e congeladas
    dentro da mesma transação utilizada para
    criar a entrevista.

    Caso qualquer etapa falhe, nada é gravado.

    Retorna o ID da entrevista criada.
    """

    # ========================================================
    # VALIDAÇÕES INICIAIS
    # ========================================================

    _validar_id(
        usuario_id,
        "Usuário"
    )


    _validar_id(
        tipo_entrevista_id,
        "Tipo de entrevista"
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
        # USUÁRIO
        # ====================================================

        usuario = _buscar_usuario_ativo(

            cursor,

            usuario_id

        )


        if usuario is None:

            raise ValueError(
                "Usuário não encontrado ou inativo."
            )


        # ====================================================
        # TIPO DE ENTREVISTA
        # ====================================================

        tipo = _buscar_tipo_entrevista_ativo(

            cursor,

            tipo_entrevista_id

        )


        if tipo is None:

            raise ValueError(
                "Tipo de entrevista não encontrado "
                "ou inativo."
            )


        # ====================================================
        # ÁREA / SUBÁREA
        # ====================================================

        (
            area,
            subarea,
            subarea_geral
        ) = _validar_contexto_area_tecnica(

            cursor,

            tipo,

            area_tecnica_id,

            subarea_tecnica_id

        )


        # ====================================================
        # SELECIONAR PERGUNTAS
        # ====================================================

        if bool(
            tipo[
                "usa_area_tecnica"
            ]
        ):

            perguntas = _buscar_perguntas_tipo_tecnico(

                cursor=cursor,

                tipo_entrevista_id=(
                    tipo_entrevista_id
                ),

                area_tecnica_id=(
                    area_tecnica_id
                ),

                subarea_tecnica_id=(
                    subarea_tecnica_id
                ),

                subarea_geral_id=(
                    subarea_geral[
                        "id"
                    ]
                )

            )


        else:

            perguntas = _buscar_perguntas_tipo_normal(

                cursor,

                tipo_entrevista_id

            )


        # ====================================================
        # PRECISA HAVER PERGUNTAS
        # ====================================================

        if not perguntas:

            if bool(
                tipo[
                    "usa_area_tecnica"
                ]
            ):

                raise ValueError(
                    "Não existem perguntas ativas "
                    "disponíveis para a área e subárea "
                    "selecionadas."
                )


            raise ValueError(
                "Não existem perguntas ativas "
                "disponíveis para este tipo de entrevista."
            )


        # ====================================================
        # CRIAR ENTREVISTA
        # ====================================================

        cursor.execute(
            """
            INSERT INTO entrevistas (

                usuario_id,

                tipo_entrevista_id,

                area_tecnica_id,

                subarea_tecnica_id,

                status

            )

            VALUES (
                ?,
                ?,
                ?,
                ?,
                'em_andamento'
            )
            """,
            (

                usuario_id,

                tipo_entrevista_id,

                (
                    area_tecnica_id

                    if area is not None

                    else None
                ),

                (
                    subarea_tecnica_id

                    if subarea is not None

                    else None
                )

            )
        )


        entrevista_id = int(
            cursor.lastrowid
        )


        # ====================================================
        # CONGELAR PERGUNTAS
        # ====================================================

        _congelar_perguntas(

            cursor,

            entrevista_id,

            perguntas

        )


        # ====================================================
        # VALIDAR SNAPSHOT CRIADO
        # ====================================================

        cursor.execute(
            """
            SELECT COUNT(*) AS quantidade

            FROM entrevista_perguntas

            WHERE entrevista_id = ?
            """,
            (
                entrevista_id,
            )
        )


        quantidade_congelada = int(
            cursor.fetchone()[
                "quantidade"
            ]
        )


        if quantidade_congelada != len(
            perguntas
        ):

            raise sqlite3.DatabaseError(
                "Não foi possível congelar corretamente "
                "todas as perguntas da entrevista."
            )


        # ====================================================
        # CONFIRMAR
        # ====================================================

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
    """

    _validar_id(
        entrevista_id,
        "ID da entrevista"
    )


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

    As mais recentes aparecem primeiro.
    """

    _validar_id(
        usuario_id,
        "Usuário"
    )


    conexao = conectar_banco()

    cursor = conexao.cursor()


    try:

        cursor.execute(
            """
            SELECT *

            FROM entrevistas

            WHERE usuario_id = ?

            ORDER BY
                data_inicio DESC,
                id DESC
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

            for registro
            in registros

        ]


    finally:

        conexao.close()


# ============================================================
# LISTAR TODAS AS ENTREVISTAS
# ============================================================

def listar_entrevistas() -> list[Entrevista]:
    """
    Retorna todas as entrevistas cadastradas.

    Utilizada principalmente pelo perfil
    Administrador.
    """

    conexao = conectar_banco()

    cursor = conexao.cursor()


    try:

        cursor.execute(
            """
            SELECT *

            FROM entrevistas

            ORDER BY
                data_inicio DESC,
                id DESC
            """
        )


        registros = cursor.fetchall()


        return [

            _registro_para_entrevista(
                registro
            )

            for registro
            in registros

        ]


    finally:

        conexao.close()


# ============================================================
# LISTAR PERGUNTAS CONGELADAS
# ============================================================

def listar_perguntas_entrevista(
    entrevista_id: int
) -> list[EntrevistaPergunta]:
    """
    Retorna exatamente as perguntas congeladas
    para determinada entrevista.

    Esta função deve ser utilizada durante a
    realização da entrevista.

    O frontend não deve reconstruir a entrevista
    consultando novamente a tabela perguntas.
    """

    _validar_id(
        entrevista_id,
        "ID da entrevista"
    )


    conexao = conectar_banco()

    cursor = conexao.cursor()


    try:

        # ----------------------------------------------------
        # GARANTIR QUE ENTREVISTA EXISTE
        # ----------------------------------------------------

        cursor.execute(
            """
            SELECT id

            FROM entrevistas

            WHERE id = ?
            """,
            (
                entrevista_id,
            )
        )


        if cursor.fetchone() is None:

            raise ValueError(
                "Entrevista não encontrada."
            )


        # ----------------------------------------------------
        # LISTAR SNAPSHOTS
        # ----------------------------------------------------

        cursor.execute(
            """
            SELECT *

            FROM entrevista_perguntas

            WHERE entrevista_id = ?

            ORDER BY

                COALESCE(
                    ordem_pergunta_aplicada,
                    999999
                ),

                id
            """,
            (
                entrevista_id,
            )
        )


        registros = cursor.fetchall()


        return [

            _registro_para_entrevista_pergunta(
                registro
            )

            for registro
            in registros

        ]


    finally:

        conexao.close()


# ============================================================
# BUSCAR PERGUNTA CONGELADA
# ============================================================

def buscar_pergunta_entrevista(
    entrevista_id: int,
    pergunta_id: int
) -> EntrevistaPergunta | None:
    """
    Verifica se determinada pergunta pertence
    ao conjunto congelado da entrevista.

    Esta função será utilizada na próxima
    adaptação de respostas.py.
    """

    _validar_id(
        entrevista_id,
        "ID da entrevista"
    )


    _validar_id(
        pergunta_id,
        "ID da pergunta"
    )


    conexao = conectar_banco()

    cursor = conexao.cursor()


    try:

        cursor.execute(
            """
            SELECT *

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


        registro = cursor.fetchone()


        if registro is None:

            return None


        return _registro_para_entrevista_pergunta(
            registro
        )


    finally:

        conexao.close()


# ============================================================
# CONTAR PERGUNTAS DA ENTREVISTA
# ============================================================

def contar_perguntas_entrevista(
    entrevista_id: int
) -> int:
    """
    Retorna a quantidade de perguntas congeladas
    para determinada entrevista.
    """

    _validar_id(
        entrevista_id,
        "ID da entrevista"
    )


    conexao = conectar_banco()

    cursor = conexao.cursor()


    try:

        cursor.execute(
            """
            SELECT COUNT(*) AS quantidade

            FROM entrevista_perguntas

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
# ALTERAR STATUS
# ============================================================

def alterar_status_entrevista(
    entrevista_id: int,
    novo_status: str
) -> bool:
    """
    Altera o status de uma entrevista.
    """

    _validar_id(
        entrevista_id,
        "ID da entrevista"
    )


    if novo_status not in STATUS_ENTREVISTA:

        raise ValueError(
            f"Status de entrevista inválido: "
            f"{novo_status}"
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


        alterada = (
            cursor.rowcount > 0
        )


        conexao.commit()


        return alterada


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

    Registra data e hora da finalização
    e altera o status para finalizada.

    Somente entrevistas em andamento
    podem ser finalizadas.

    A regra atual de quantidade mínima de
    respostas permanece sendo controlada
    pela camada de rota.
    """

    _validar_id(
        entrevista_id,
        "ID da entrevista"
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
                status

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


        if (
            registro[
                "status"
            ]
            != "em_andamento"
        ):

            raise ValueError(
                "Somente entrevistas em andamento "
                "podem ser finalizadas."
            )


        cursor.execute(
            """
            UPDATE entrevistas

            SET

                status = 'finalizada',

                data_fim = ?

            WHERE id = ?
            """,
            (
                _agora_utc(),
                entrevista_id
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
# CANCELAR ENTREVISTA
# ============================================================

def cancelar_entrevista(
    entrevista_id: int
) -> bool:
    """
    Cancela uma entrevista em andamento.

    Entrevistas que não estejam em andamento
    não podem ser canceladas.
    """

    _validar_id(
        entrevista_id,
        "ID da entrevista"
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
                status

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


        if (
            registro[
                "status"
            ]
            != "em_andamento"
        ):

            raise ValueError(
                "Somente entrevistas em andamento "
                "podem ser canceladas."
            )


        cursor.execute(
            """
            UPDATE entrevistas

            SET

                status = 'cancelada',

                data_fim = ?

            WHERE id = ?
            """,
            (
                _agora_utc(),
                entrevista_id
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
# REGISTRAR PONTUAÇÃO FINAL
# ============================================================

def registrar_pontuacao_final(
    entrevista_id: int,
    pontuacao: float
) -> bool:
    """
    Registra a pontuação final de uma entrevista.

    A escala permanece de 0 a 10.
    """

    _validar_id(
        entrevista_id,
        "ID da entrevista"
    )


    if (
        pontuacao < 0
        or pontuacao > 10
    ):

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


        alterada = (
            cursor.rowcount > 0
        )


        conexao.commit()


        return alterada


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

    _validar_id(
        entrevista_id,
        "ID da entrevista"
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
# CONVERTER REGISTRO EM ENTREVISTA
# ============================================================

def _registro_para_entrevista(
    registro: sqlite3.Row
) -> Entrevista:
    """
    Converte um registro SQLite em Entrevista.

    A função é compatível com os novos campos
    de snapshot de tipo, área e subárea.
    """

    colunas = registro.keys()


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
        ],

        tipo_entrevista_nome_aplicado=(

            registro[
                "tipo_entrevista_nome_aplicado"
            ]

            if (
                "tipo_entrevista_nome_aplicado"
                in colunas
            )

            else None
        ),

        tipo_entrevista_descricao_aplicada=(

            registro[
                "tipo_entrevista_descricao_aplicada"
            ]

            if (
                "tipo_entrevista_descricao_aplicada"
                in colunas
            )

            else None
        ),

        area_tecnica_id=(

            registro[
                "area_tecnica_id"
            ]

            if (
                "area_tecnica_id"
                in colunas
            )

            else None
        ),

        subarea_tecnica_id=(

            registro[
                "subarea_tecnica_id"
            ]

            if (
                "subarea_tecnica_id"
                in colunas
            )

            else None
        ),

        area_tecnica_nome_aplicado=(

            registro[
                "area_tecnica_nome_aplicado"
            ]

            if (
                "area_tecnica_nome_aplicado"
                in colunas
            )

            else None
        ),

        subarea_tecnica_nome_aplicado=(

            registro[
                "subarea_tecnica_nome_aplicado"
            ]

            if (
                "subarea_tecnica_nome_aplicado"
                in colunas
            )

            else None
        )

    )


# ============================================================
# CONVERTER REGISTRO EM PERGUNTA DA ENTREVISTA
# ============================================================

def _registro_para_entrevista_pergunta(
    registro: sqlite3.Row
) -> EntrevistaPergunta:
    """
    Converte um registro de entrevista_perguntas
    em EntrevistaPergunta.
    """

    return EntrevistaPergunta(

        id=registro[
            "id"
        ],

        entrevista_id=registro[
            "entrevista_id"
        ],

        pergunta_id=registro[
            "pergunta_id"
        ],

        pergunta_texto_aplicado=registro[
            "pergunta_texto_aplicado"
        ],

        exemplo_esperado_aplicado=registro[
            "exemplo_esperado_aplicado"
        ],

        competencia_id_aplicada=registro[
            "competencia_id_aplicada"
        ],

        competencia_nome_aplicada=registro[
            "competencia_nome_aplicada"
        ],

        area_tecnica_id_aplicada=registro[
            "area_tecnica_id_aplicada"
        ],

        area_tecnica_nome_aplicada=registro[
            "area_tecnica_nome_aplicada"
        ],

        subarea_tecnica_id_aplicada=registro[
            "subarea_tecnica_id_aplicada"
        ],

        subarea_tecnica_nome_aplicada=registro[
            "subarea_tecnica_nome_aplicada"
        ],

        peso_pergunta_aplicado=registro[
            "peso_pergunta_aplicado"
        ],

        usa_star_aplicado=bool(
            registro[
                "usa_star_aplicado"
            ]
        ),

        ordem_pergunta_aplicada=registro[
            "ordem_pergunta_aplicada"
        ],

        data_aplicacao=registro[
            "data_aplicacao"
        ]

    )