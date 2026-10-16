"""
perguntas.py

Módulo responsável pelo gerenciamento das perguntas
do Simulador de Entrevistas.

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
- filtrar perguntas por área técnica;
- filtrar perguntas por subárea técnica;
- validar vínculos com tipos de entrevista;
- validar vínculos com competências;
- validar vínculos com áreas técnicas;
- validar vínculos com subáreas técnicas;
- preparar a seleção de perguntas técnicas para entrevistas.

Regras de perguntas técnicas:

- quando o tipo de entrevista utiliza área técnica,
  área e subárea são obrigatórias;
- a área precisa existir e estar ativa;
- a subárea precisa existir e estar ativa;
- a subárea precisa pertencer à área;
- tipos que não utilizam área técnica não podem
  possuir área ou subárea vinculada.

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
# VALIDAR CAMPOS BÁSICOS
# ============================================================

def _validar_campos_pergunta(
    pergunta: Pergunta
) -> None:
    """
    Valida os campos básicos da pergunta.

    As referências ao banco são verificadas
    separadamente.
    """

    # --------------------------------------------------------
    # TEXTO
    # --------------------------------------------------------

    if pergunta.texto is None:

        raise ValueError(
            "O texto da pergunta é obrigatório."
        )


    texto = pergunta.texto.strip()


    if not texto:

        raise ValueError(
            "O texto da pergunta não pode estar vazio."
        )


    if len(texto) < 3:

        raise ValueError(
            "O texto da pergunta deve possuir "
            "pelo menos 3 caracteres."
        )


    # --------------------------------------------------------
    # TIPO DE ENTREVISTA
    # --------------------------------------------------------

    _validar_id(
        pergunta.tipo_entrevista_id,
        "Tipo de entrevista"
    )


    # --------------------------------------------------------
    # COMPETÊNCIA
    # --------------------------------------------------------

    _validar_id(
        pergunta.competencia_id,
        "Competência"
    )


    # --------------------------------------------------------
    # PESO
    # --------------------------------------------------------

    if pergunta.peso is None:

        raise ValueError(
            "O peso da pergunta é obrigatório."
        )


    if pergunta.peso <= 0:

        raise ValueError(
            "O peso da pergunta deve ser maior "
            "que zero."
        )


    # --------------------------------------------------------
    # ORDEM
    # --------------------------------------------------------

    if (
        pergunta.ordem is not None
        and pergunta.ordem <= 0
    ):

        raise ValueError(
            "A ordem da pergunta deve ser "
            "maior que zero."
        )


# ============================================================
# BUSCAR TIPO DE ENTREVISTA
# ============================================================

def _buscar_tipo_entrevista(
    cursor: sqlite3.Cursor,
    tipo_entrevista_id: int
):
    """
    Busca o tipo de entrevista dentro da
    conexão atualmente utilizada.
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

        WHERE id = ?
        """,
        (
            tipo_entrevista_id,
        )
    )


    return cursor.fetchone()


# ============================================================
# BUSCAR COMPETÊNCIA
# ============================================================

def _buscar_competencia(
    cursor: sqlite3.Cursor,
    competencia_id: int
):
    """
    Busca uma competência dentro da
    conexão atual.
    """

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


    return cursor.fetchone()


# ============================================================
# BUSCAR ÁREA
# ============================================================

def _buscar_area_tecnica(
    cursor: sqlite3.Cursor,
    area_tecnica_id: int
):
    """
    Busca uma área técnica.
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

        WHERE id = ?
        """,
        (
            area_tecnica_id,
        )
    )


    return cursor.fetchone()


# ============================================================
# BUSCAR SUBÁREA
# ============================================================

def _buscar_subarea_tecnica(
    cursor: sqlite3.Cursor,
    subarea_tecnica_id: int
):
    """
    Busca uma subárea técnica.
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

        WHERE id = ?
        """,
        (
            subarea_tecnica_id,
        )
    )


    return cursor.fetchone()


# ============================================================
# VALIDAR REFERÊNCIAS
# ============================================================

def _validar_referencias_pergunta(
    cursor: sqlite3.Cursor,
    pergunta: Pergunta,
    exigir_ativos: bool = True
) -> None:
    """
    Valida todos os relacionamentos utilizados
    por uma pergunta.

    Quando exigir_ativos for True:

    - tipo de entrevista precisa estar ativo;
    - competência precisa estar ativa;
    - área precisa estar ativa;
    - subárea precisa estar ativa.
    """

    # ========================================================
    # TIPO DE ENTREVISTA
    # ========================================================

    tipo = _buscar_tipo_entrevista(

        cursor,

        pergunta.tipo_entrevista_id

    )


    if tipo is None:

        raise ValueError(
            "Tipo de entrevista não encontrado."
        )


    if (
        exigir_ativos
        and not bool(
            tipo[
                "ativo"
            ]
        )
    ):

        raise ValueError(
            "O tipo de entrevista informado "
            "está inativo."
        )


    # ========================================================
    # COMPETÊNCIA
    # ========================================================

    competencia = _buscar_competencia(

        cursor,

        pergunta.competencia_id

    )


    if competencia is None:

        raise ValueError(
            "Competência não encontrada."
        )


    if (
        exigir_ativos
        and not bool(
            competencia[
                "ativa"
            ]
        )
    ):

        raise ValueError(
            "A competência informada está inativa."
        )


    # ========================================================
    # TIPO UTILIZA ÁREA TÉCNICA?
    # ========================================================

    usa_area_tecnica = bool(
        tipo[
            "usa_area_tecnica"
        ]
    )


    # ========================================================
    # TIPO TÉCNICO
    # ========================================================

    if usa_area_tecnica:

        # ----------------------------------------------------
        # ÁREA OBRIGATÓRIA
        # ----------------------------------------------------

        if pergunta.area_tecnica_id is None:

            raise ValueError(
                "A área técnica é obrigatória "
                "para este tipo de entrevista."
            )


        _validar_id(
            pergunta.area_tecnica_id,
            "Área técnica"
        )


        # ----------------------------------------------------
        # SUBÁREA OBRIGATÓRIA
        # ----------------------------------------------------

        if pergunta.subarea_tecnica_id is None:

            raise ValueError(
                "A subárea técnica é obrigatória "
                "para este tipo de entrevista."
            )


        _validar_id(
            pergunta.subarea_tecnica_id,
            "Subárea técnica"
        )


        # ----------------------------------------------------
        # VALIDAR ÁREA
        # ----------------------------------------------------

        area = _buscar_area_tecnica(

            cursor,

            pergunta.area_tecnica_id

        )


        if area is None:

            raise ValueError(
                "Área técnica não encontrada."
            )


        if (
            exigir_ativos
            and not bool(
                area[
                    "ativo"
                ]
            )
        ):

            raise ValueError(
                "A área técnica informada "
                "está inativa."
            )


        # ----------------------------------------------------
        # VALIDAR SUBÁREA
        # ----------------------------------------------------

        subarea = _buscar_subarea_tecnica(

            cursor,

            pergunta.subarea_tecnica_id

        )


        if subarea is None:

            raise ValueError(
                "Subárea técnica não encontrada."
            )


        # ----------------------------------------------------
        # VALIDAR VÍNCULO ÁREA / SUBÁREA
        # ----------------------------------------------------

        if (
            subarea[
                "area_tecnica_id"
            ]
            != pergunta.area_tecnica_id
        ):

            raise ValueError(
                "A subárea informada não pertence "
                "à área técnica selecionada."
            )


        if (
            exigir_ativos
            and not bool(
                subarea[
                    "ativo"
                ]
            )
        ):

            raise ValueError(
                "A subárea técnica informada "
                "está inativa."
            )


    # ========================================================
    # TIPO NÃO UTILIZA ÁREA
    # ========================================================

    else:

        if (
            pergunta.area_tecnica_id
            is not None

            or

            pergunta.subarea_tecnica_id
            is not None
        ):

            raise ValueError(
                "Este tipo de entrevista não utiliza "
                "área ou subárea técnica."
            )


# ============================================================
# VALIDAR PERGUNTA
# ============================================================

def validar_pergunta(
    pergunta: Pergunta
) -> None:
    """
    Executa todas as validações necessárias
    para uma pergunta.
    """

    _validar_campos_pergunta(
        pergunta
    )


    conexao = conectar_banco()

    cursor = conexao.cursor()


    try:

        _validar_referencias_pergunta(

            cursor,

            pergunta,

            exigir_ativos=True

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
    Cadastra uma nova pergunta.

    Para perguntas técnicas:

    - área é obrigatória;
    - subárea é obrigatória;
    - ambas precisam estar ativas;
    - a subárea precisa pertencer à área.
    """

    _validar_campos_pergunta(
        pergunta
    )


    conexao = conectar_banco()

    cursor = conexao.cursor()


    try:

        cursor.execute(
            """
            BEGIN IMMEDIATE
            """
        )


        _validar_referencias_pergunta(

            cursor,

            pergunta,

            exigir_ativos=True

        )


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

                usa_star,

                area_tecnica_id,

                subarea_tecnica_id

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
                ?
            )
            """,
            (

                pergunta.tipo_entrevista_id,

                pergunta.competencia_id,

                pergunta.texto.strip(),

                (
                    pergunta.exemplo_esperado.strip()

                    if (
                        pergunta.exemplo_esperado
                        is not None
                        and pergunta.exemplo_esperado.strip()
                    )

                    else None
                ),

                pergunta.ordem,

                (
                    1
                    if pergunta.ativa
                    else 0
                ),

                pergunta.peso,

                (
                    1
                    if pergunta.usa_star
                    else 0
                ),

                pergunta.area_tecnica_id,

                pergunta.subarea_tecnica_id

            )
        )


        pergunta_id = cursor.lastrowid


        conexao.commit()


        return int(
            pergunta_id
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
# LISTAR PERGUNTAS
# ============================================================

def listar_perguntas(
    somente_ativas: bool = False,
    tipo_entrevista_id: int | None = None,
    competencia_id: int | None = None,
    area_tecnica_id: int | None = None,
    subarea_tecnica_id: int | None = None
) -> list[Pergunta]:
    """
    Lista as perguntas cadastradas.

    Permite filtros por:

    - status;
    - tipo de entrevista;
    - competência;
    - área técnica;
    - subárea técnica.

    Quando somente_ativas=True, também são
    considerados os status dos registros pais.

    Assim, uma pergunta ativa vinculada a tipo,
    competência, área ou subárea inativos não
    será disponibilizada para uso.
    """

    conexao = conectar_banco()

    cursor = conexao.cursor()


    try:

        condicoes = []

        parametros = []


        # ----------------------------------------------------
        # SOMENTE ATIVAS
        # ----------------------------------------------------

        if somente_ativas:

            condicoes.append(
                "p.ativa = 1"
            )

            condicoes.append(
                "te.ativo = 1"
            )

            condicoes.append(
                "c.ativa = 1"
            )


            # Para tipos que utilizam área técnica,
            # área e subárea precisam existir,
            # estar ativas e possuir vínculo correto.

            condicoes.append(
                """
                (
                    te.usa_area_tecnica = 0

                    OR

                    (
                        p.area_tecnica_id IS NOT NULL

                        AND

                        p.subarea_tecnica_id IS NOT NULL

                        AND

                        a.ativo = 1

                        AND

                        s.ativo = 1

                        AND

                        s.area_tecnica_id =
                            p.area_tecnica_id
                    )
                )
                """
            )


        # ----------------------------------------------------
        # FILTRO POR TIPO
        # ----------------------------------------------------

        if tipo_entrevista_id is not None:

            _validar_id(
                tipo_entrevista_id,
                "Tipo de entrevista"
            )

            condicoes.append(
                "p.tipo_entrevista_id = ?"
            )

            parametros.append(
                tipo_entrevista_id
            )


        # ----------------------------------------------------
        # FILTRO POR COMPETÊNCIA
        # ----------------------------------------------------

        if competencia_id is not None:

            _validar_id(
                competencia_id,
                "Competência"
            )

            condicoes.append(
                "p.competencia_id = ?"
            )

            parametros.append(
                competencia_id
            )


        # ----------------------------------------------------
        # FILTRO POR ÁREA
        # ----------------------------------------------------

        if area_tecnica_id is not None:

            _validar_id(
                area_tecnica_id,
                "Área técnica"
            )

            condicoes.append(
                "p.area_tecnica_id = ?"
            )

            parametros.append(
                area_tecnica_id
            )


        # ----------------------------------------------------
        # FILTRO POR SUBÁREA
        # ----------------------------------------------------

        if subarea_tecnica_id is not None:

            _validar_id(
                subarea_tecnica_id,
                "Subárea técnica"
            )

            condicoes.append(
                "p.subarea_tecnica_id = ?"
            )

            parametros.append(
                subarea_tecnica_id
            )


        where = ""


        if condicoes:

            where = (
                "WHERE "
                + " AND ".join(
                    condicoes
                )
            )


        cursor.execute(
            f"""
            SELECT
                p.*

            FROM perguntas p

            INNER JOIN tipos_entrevista te

                ON te.id =
                    p.tipo_entrevista_id

            INNER JOIN competencias c

                ON c.id =
                    p.competencia_id

            LEFT JOIN areas_tecnicas a

                ON a.id =
                    p.area_tecnica_id

            LEFT JOIN subareas_tecnicas s

                ON s.id =
                    p.subarea_tecnica_id

            {where}

            ORDER BY

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


        registros = cursor.fetchall()


        return [

            _registro_para_pergunta(
                registro
            )

            for registro
            in registros

        ]


    finally:

        conexao.close()


# ============================================================
# BUSCAR PERGUNTA
# ============================================================

def buscar_pergunta(
    pergunta_id: int
) -> Pergunta | None:
    """
    Busca uma pergunta pelo ID.
    """

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

            FROM perguntas

            WHERE id = ?
            """,
            (
                pergunta_id,
            )
        )


        registro = cursor.fetchone()


        if registro is None:

            return None


        return _registro_para_pergunta(
            registro
        )


    finally:

        conexao.close()


# ============================================================
# BUSCAR PERGUNTA ATIVA
# ============================================================

def buscar_pergunta_ativa(
    pergunta_id: int
) -> Pergunta | None:
    """
    Busca uma pergunta somente quando ela
    estiver disponível para utilização.

    Além do status da própria pergunta,
    os registros pais precisam estar ativos.
    """

    _validar_id(
        pergunta_id,
        "ID da pergunta"
    )


    perguntas = listar_perguntas(
        somente_ativas=True
    )


    for pergunta in perguntas:

        if pergunta.id == pergunta_id:

            return pergunta


    return None


# ============================================================
# LISTAR POR TIPO
# ============================================================

def listar_perguntas_por_tipo(
    tipo_entrevista_id: int,
    somente_ativas: bool = True
) -> list[Pergunta]:
    """
    Lista perguntas de determinado
    tipo de entrevista.
    """

    return listar_perguntas(

        somente_ativas=(
            somente_ativas
        ),

        tipo_entrevista_id=(
            tipo_entrevista_id
        )

    )


# ============================================================
# LISTAR POR COMPETÊNCIA
# ============================================================

def listar_perguntas_por_competencia(
    competencia_id: int,
    somente_ativas: bool = True
) -> list[Pergunta]:
    """
    Lista perguntas de determinada competência.
    """

    return listar_perguntas(

        somente_ativas=(
            somente_ativas
        ),

        competencia_id=(
            competencia_id
        )

    )


# ============================================================
# LISTAR POR ÁREA
# ============================================================

def listar_perguntas_por_area(
    area_tecnica_id: int,
    somente_ativas: bool = True
) -> list[Pergunta]:
    """
    Lista perguntas de determinada área técnica.
    """

    return listar_perguntas(

        somente_ativas=(
            somente_ativas
        ),

        area_tecnica_id=(
            area_tecnica_id
        )

    )


# ============================================================
# LISTAR POR SUBÁREA
# ============================================================

def listar_perguntas_por_subarea(
    subarea_tecnica_id: int,
    somente_ativas: bool = True
) -> list[Pergunta]:
    """
    Lista perguntas vinculadas diretamente
    a determinada subárea.
    """

    return listar_perguntas(

        somente_ativas=(
            somente_ativas
        ),

        subarea_tecnica_id=(
            subarea_tecnica_id
        )

    )


# ============================================================
# LISTAR PERGUNTAS PARA ENTREVISTA TÉCNICA
# ============================================================

def listar_perguntas_tecnicas(
    area_tecnica_id: int,
    subarea_tecnica_id: int,
    incluir_geral: bool = True
) -> list[Pergunta]:
    """
    Retorna as perguntas que poderão compor
    uma entrevista técnica.

    Regra aprovada:

    Se a subárea escolhida for específica:

        perguntas da área / Geral
        +
        perguntas da área / subárea escolhida

    Se a subárea escolhida já for Geral:

        apenas perguntas da área / Geral

    A utilização definitiva desta função para
    congelar as perguntas ocorrerá na etapa
    de criação da entrevista.
    """

    _validar_id(
        area_tecnica_id,
        "Área técnica"
    )


    _validar_id(
        subarea_tecnica_id,
        "Subárea técnica"
    )


    conexao = conectar_banco()

    cursor = conexao.cursor()


    try:

        # ====================================================
        # VALIDAR ÁREA
        # ====================================================

        area = _buscar_area_tecnica(

            cursor,

            area_tecnica_id

        )


        if area is None:

            raise ValueError(
                "Área técnica não encontrada."
            )


        if not bool(
            area[
                "ativo"
            ]
        ):

            raise ValueError(
                "A área técnica selecionada "
                "está inativa."
            )


        # ====================================================
        # VALIDAR SUBÁREA
        # ====================================================

        subarea = _buscar_subarea_tecnica(

            cursor,

            subarea_tecnica_id

        )


        if subarea is None:

            raise ValueError(
                "Subárea técnica não encontrada."
            )


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


        if not bool(
            subarea[
                "ativo"
            ]
        ):

            raise ValueError(
                "A subárea técnica selecionada "
                "está inativa."
            )


        # ====================================================
        # LOCALIZAR GERAL
        # ====================================================

        cursor.execute(
            """
            SELECT id

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


        geral = cursor.fetchone()


        if geral is None:

            raise ValueError(
                "A área técnica não possui uma "
                "subárea Geral ativa."
            )


        geral_id = int(
            geral[
                "id"
            ]
        )


        # ====================================================
        # DEFINIR SUBÁREAS UTILIZADAS
        # ====================================================

        subareas_ids = [
            subarea_tecnica_id
        ]


        if (
            incluir_geral

            and

            subarea_tecnica_id
            != geral_id
        ):

            subareas_ids.insert(
                0,
                geral_id
            )


        placeholders = ",".join(
            "?"
            for _ in subareas_ids
        )


        parametros = [

            area_tecnica_id,

            *subareas_ids

        ]


        # ====================================================
        # BUSCAR PERGUNTAS
        # ====================================================

        cursor.execute(
            f"""
            SELECT
                p.*

            FROM perguntas p

            INNER JOIN tipos_entrevista te

                ON te.id =
                    p.tipo_entrevista_id

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
                p.ativa = 1

              AND
                te.ativo = 1

              AND
                te.usa_area_tecnica = 1

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

                    WHEN
                        p.subarea_tecnica_id = {geral_id}

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


        registros = cursor.fetchall()


        return [

            _registro_para_pergunta(
                registro
            )

            for registro
            in registros

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

    As mesmas regras utilizadas no cadastro
    são aplicadas na edição.
    """

    _validar_id(
        pergunta_id,
        "ID da pergunta"
    )


    _validar_campos_pergunta(
        pergunta
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

            FROM perguntas

            WHERE id = ?
            """,
            (
                pergunta_id,
            )
        )


        if cursor.fetchone() is None:

            conexao.rollback()

            return False


        _validar_referencias_pergunta(

            cursor,

            pergunta,

            exigir_ativos=True

        )


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

                usa_star = ?,

                area_tecnica_id = ?,

                subarea_tecnica_id = ?

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
                        is not None
                        and pergunta.exemplo_esperado.strip()
                    )

                    else None
                ),

                pergunta.ordem,

                (
                    1
                    if pergunta.ativa
                    else 0
                ),

                pergunta.peso,

                (
                    1
                    if pergunta.usa_star
                    else 0
                ),

                pergunta.area_tecnica_id,

                pergunta.subarea_tecnica_id,

                pergunta_id

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
# DESATIVAR PERGUNTA
# ============================================================

def desativar_pergunta(
    pergunta_id: int
) -> bool:
    """
    Desativa uma pergunta.

    O registro permanece no banco para
    preservação histórica.
    """

    _validar_id(
        pergunta_id,
        "ID da pergunta"
    )


    conexao = conectar_banco()

    cursor = conexao.cursor()


    try:

        cursor.execute(
            """
            UPDATE perguntas

            SET ativa = 0

            WHERE id = ?
            """,
            (
                pergunta_id,
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
# REATIVAR PERGUNTA
# ============================================================

def reativar_pergunta(
    pergunta_id: int
) -> bool:
    """
    Reativa uma pergunta.

    Antes da reativação são validados:

    - tipo de entrevista;
    - competência;
    - área;
    - subárea;
    - status de todos os registros relacionados.
    """

    _validar_id(
        pergunta_id,
        "ID da pergunta"
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
            SELECT *

            FROM perguntas

            WHERE id = ?
            """,
            (
                pergunta_id,
            )
        )


        registro = cursor.fetchone()


        if registro is None:

            conexao.rollback()

            return False


        pergunta = _registro_para_pergunta(
            registro
        )


        _validar_campos_pergunta(
            pergunta
        )


        _validar_referencias_pergunta(

            cursor,

            pergunta,

            exigir_ativos=True

        )


        cursor.execute(
            """
            UPDATE perguntas

            SET ativa = 1

            WHERE id = ?
            """,
            (
                pergunta_id,
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
# EXCLUIR PERGUNTA
# ============================================================

def excluir_pergunta(
    pergunta_id: int
) -> bool:
    """
    Exclui fisicamente uma pergunta apenas quando
    ela nunca tiver sido utilizada.

    Caso tenha sido utilizada em:

    - respostas;
    - conjunto congelado de uma entrevista;

    a exclusão é bloqueada.

    Para preservação histórica, o comportamento
    normal da administração deve ser inativar.
    """

    _validar_id(
        pergunta_id,
        "ID da pergunta"
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
        # VERIFICAR EXISTÊNCIA
        # ====================================================

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

            conexao.rollback()

            return False


        # ====================================================
        # VERIFICAR RESPOSTAS
        # ====================================================

        cursor.execute(
            """
            SELECT COUNT(*) AS quantidade

            FROM respostas

            WHERE pergunta_id = ?
            """,
            (
                pergunta_id,
            )
        )


        quantidade_respostas = int(
            cursor.fetchone()[
                "quantidade"
            ]
        )


        if quantidade_respostas > 0:

            raise ValueError(
                "A pergunta não pode ser excluída "
                "porque já foi utilizada em uma "
                "entrevista. Utilize a opção de "
                "inativação."
            )


        # ====================================================
        # VERIFICAR SNAPSHOT DE ENTREVISTA
        # ====================================================

        cursor.execute(
            """
            SELECT COUNT(*) AS quantidade

            FROM entrevista_perguntas

            WHERE pergunta_id = ?
            """,
            (
                pergunta_id,
            )
        )


        quantidade_snapshots = int(
            cursor.fetchone()[
                "quantidade"
            ]
        )


        if quantidade_snapshots > 0:

            raise ValueError(
                "A pergunta não pode ser excluída "
                "porque faz parte do conjunto histórico "
                "de uma entrevista. Utilize a opção de "
                "inativação."
            )


        # ====================================================
        # EXCLUIR
        # ====================================================

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
# CONVERTER REGISTRO SQLITE
# ============================================================

def _registro_para_pergunta(
    registro: sqlite3.Row
) -> Pergunta:
    """
    Converte um registro SQLite em Pergunta.
    """

    colunas = (
        registro.keys()
    )


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
        ],

        area_tecnica_id=(

            registro[
                "area_tecnica_id"
            ]

            if "area_tecnica_id"
            in colunas

            else None
        ),

        subarea_tecnica_id=(

            registro[
                "subarea_tecnica_id"
            ]

            if "subarea_tecnica_id"
            in colunas

            else None
        )

    )