"""Funções responsáveis pelo gerenciamento das perguntas do simulador."""

import sqlite3

try:
    from .database import conectar_banco
    from .models import Pergunta
except ImportError:
    from database import conectar_banco
    from models import Pergunta


def _validar_id(valor: int | None, campo: str) -> None:
    """Confere se um identificador foi informado e é maior que zero."""
    if valor is None or valor <= 0:
        raise ValueError(f"{campo} inválido.")


def _validar_campos_pergunta(pergunta: Pergunta) -> None:
    """Valida os campos básicos da pergunta antes de consultar os relacionamentos no banco."""
    # O texto precisa existir e ter um tamanho mínimo para ser uma pergunta válida.
    if pergunta.texto is None:
        raise ValueError("O texto da pergunta é obrigatório.")

    texto = pergunta.texto.strip()

    if not texto:
        raise ValueError("O texto da pergunta não pode estar vazio.")

    if len(texto) < 3:
        raise ValueError("O texto da pergunta deve possuir pelo menos 3 caracteres.")

    # Tipo de entrevista e competência são obrigatórios em qualquer pergunta.
    _validar_id(pergunta.tipo_entrevista_id, "Tipo de entrevista")
    _validar_id(pergunta.competencia_id, "Competência")

    # Peso e ordem precisam respeitar valores positivos.
    if pergunta.peso is None:
        raise ValueError("O peso da pergunta é obrigatório.")

    if pergunta.peso <= 0:
        raise ValueError("O peso da pergunta deve ser maior que zero.")

    if pergunta.ordem is not None and pergunta.ordem <= 0:
        raise ValueError("A ordem da pergunta deve ser maior que zero.")


def _buscar_tipo_entrevista(cursor: sqlite3.Cursor, tipo_entrevista_id: int):
    """Busca o tipo de entrevista usando a conexão que já está aberta."""
    cursor.execute(
        """
        SELECT id, nome, descricao, ativo, usa_area_tecnica
        FROM tipos_entrevista
        WHERE id = ?
        """,
        (tipo_entrevista_id,)
    )

    return cursor.fetchone()


def _buscar_competencia(cursor: sqlite3.Cursor, competencia_id: int):
    """Busca a competência usando a conexão que já está aberta."""
    cursor.execute(
        """
        SELECT id, nome, descricao, ativa
        FROM competencias
        WHERE id = ?
        """,
        (competencia_id,)
    )

    return cursor.fetchone()


def _buscar_area_tecnica(cursor: sqlite3.Cursor, area_tecnica_id: int):
    """Busca uma área técnica dentro da operação atual."""
    cursor.execute(
        """
        SELECT id, nome, descricao, ativo, ordem
        FROM areas_tecnicas
        WHERE id = ?
        """,
        (area_tecnica_id,)
    )

    return cursor.fetchone()


def _buscar_subarea_tecnica(cursor: sqlite3.Cursor, subarea_tecnica_id: int):
    """Busca uma subárea técnica dentro da operação atual."""
    cursor.execute(
        """
        SELECT id, area_tecnica_id, nome, descricao, eh_geral, ativo, ordem
        FROM subareas_tecnicas
        WHERE id = ?
        """,
        (subarea_tecnica_id,)
    )

    return cursor.fetchone()


def _validar_referencias_pergunta(
    cursor: sqlite3.Cursor,
    pergunta: Pergunta,
    exigir_ativos: bool = True
) -> None:
    """Valida tipo, competência e, quando necessário, área e subárea da pergunta."""
    # Primeiro confere se o tipo de entrevista existe e pode ser usado.
    tipo = _buscar_tipo_entrevista(cursor, pergunta.tipo_entrevista_id)

    if tipo is None:
        raise ValueError("Tipo de entrevista não encontrado.")

    if exigir_ativos and not bool(tipo["ativo"]):
        raise ValueError("O tipo de entrevista informado está inativo.")

    # Depois verifica a competência associada à pergunta.
    competencia = _buscar_competencia(cursor, pergunta.competencia_id)

    if competencia is None:
        raise ValueError("Competência não encontrada.")

    if exigir_ativos and not bool(competencia["ativa"]):
        raise ValueError("A competência informada está inativa.")

    # A própria configuração do tipo define se área e subárea são obrigatórias.
    usa_area_tecnica = bool(tipo["usa_area_tecnica"])

    if usa_area_tecnica:
        if pergunta.area_tecnica_id is None:
            raise ValueError("A área técnica é obrigatória para este tipo de entrevista.")

        if pergunta.subarea_tecnica_id is None:
            raise ValueError("A subárea técnica é obrigatória para este tipo de entrevista.")

        _validar_id(pergunta.area_tecnica_id, "Área técnica")
        _validar_id(pergunta.subarea_tecnica_id, "Subárea técnica")

        # A área técnica precisa existir e, para novas operações, estar ativa.
        area = _buscar_area_tecnica(cursor, pergunta.area_tecnica_id)

        if area is None:
            raise ValueError("Área técnica não encontrada.")

        if exigir_ativos and not bool(area["ativo"]):
            raise ValueError("A área técnica informada está inativa.")

        # A subárea precisa existir, pertencer à área e também estar ativa.
        subarea = _buscar_subarea_tecnica(cursor, pergunta.subarea_tecnica_id)

        if subarea is None:
            raise ValueError("Subárea técnica não encontrada.")

        if subarea["area_tecnica_id"] != pergunta.area_tecnica_id:
            raise ValueError("A subárea informada não pertence à área técnica selecionada.")

        if exigir_ativos and not bool(subarea["ativo"]):
            raise ValueError("A subárea técnica informada está inativa.")

    else:
        # Perguntas não técnicas não podem guardar vínculos técnicos.
        if pergunta.area_tecnica_id is not None or pergunta.subarea_tecnica_id is not None:
            raise ValueError("Este tipo de entrevista não utiliza área ou subárea técnica.")


def validar_pergunta(pergunta: Pergunta) -> None:
    """Executa todas as validações necessárias para uma pergunta."""
    _validar_campos_pergunta(pergunta)

    conexao = conectar_banco()
    cursor = conexao.cursor()

    try:
        _validar_referencias_pergunta(cursor, pergunta, exigir_ativos=True)
    finally:
        conexao.close()


def cadastrar_pergunta(pergunta: Pergunta) -> int:
    """Cadastra uma pergunta depois de validar todos os dados e relacionamentos."""
    _validar_campos_pergunta(pergunta)

    conexao = conectar_banco()
    cursor = conexao.cursor()

    try:
        # A validação e o INSERT ficam na mesma transação para evitar alterações entre as etapas.
        cursor.execute("BEGIN IMMEDIATE")
        _validar_referencias_pergunta(cursor, pergunta, exigir_ativos=True)

        exemplo_esperado = None

        if pergunta.exemplo_esperado is not None and pergunta.exemplo_esperado.strip():
            exemplo_esperado = pergunta.exemplo_esperado.strip()

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
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                pergunta.tipo_entrevista_id,
                pergunta.competencia_id,
                pergunta.texto.strip(),
                exemplo_esperado,
                pergunta.ordem,
                1 if pergunta.ativa else 0,
                pergunta.peso,
                1 if pergunta.usa_star else 0,
                pergunta.area_tecnica_id,
                pergunta.subarea_tecnica_id
            )
        )

        pergunta_id = cursor.lastrowid

        conexao.commit()

        return int(pergunta_id)

    except (sqlite3.Error, ValueError):
        conexao.rollback()
        raise
    finally:
        conexao.close()


def listar_perguntas(
    somente_ativas: bool = False,
    tipo_entrevista_id: int | None = None,
    competencia_id: int | None = None,
    area_tecnica_id: int | None = None,
    subarea_tecnica_id: int | None = None
) -> list[Pergunta]:
    """Lista perguntas e permite aplicar filtros administrativos e técnicos."""
    conexao = conectar_banco()
    cursor = conexao.cursor()

    try:
        condicoes = []
        parametros = []

        # Para uso em entrevistas, a pergunta e todos os registros pais precisam estar ativos.
        if somente_ativas:
            condicoes.append("p.ativa = 1")
            condicoes.append("te.ativo = 1")
            condicoes.append("c.ativa = 1")

            condicoes.append(
                """
                (
                    te.usa_area_tecnica = 0
                    OR (
                        p.area_tecnica_id IS NOT NULL
                        AND p.subarea_tecnica_id IS NOT NULL
                        AND a.ativo = 1
                        AND s.ativo = 1
                        AND s.area_tecnica_id = p.area_tecnica_id
                    )
                )
                """
            )

        # Cada filtro informado adiciona uma condição simples à consulta.
        if tipo_entrevista_id is not None:
            _validar_id(tipo_entrevista_id, "Tipo de entrevista")
            condicoes.append("p.tipo_entrevista_id = ?")
            parametros.append(tipo_entrevista_id)

        if competencia_id is not None:
            _validar_id(competencia_id, "Competência")
            condicoes.append("p.competencia_id = ?")
            parametros.append(competencia_id)

        if area_tecnica_id is not None:
            _validar_id(area_tecnica_id, "Área técnica")
            condicoes.append("p.area_tecnica_id = ?")
            parametros.append(area_tecnica_id)

        if subarea_tecnica_id is not None:
            _validar_id(subarea_tecnica_id, "Subárea técnica")
            condicoes.append("p.subarea_tecnica_id = ?")
            parametros.append(subarea_tecnica_id)

        where = ""

        if condicoes:
            where = "WHERE " + " AND ".join(condicoes)

        cursor.execute(
            f"""
            SELECT p.*
            FROM perguntas p
            INNER JOIN tipos_entrevista te ON te.id = p.tipo_entrevista_id
            INNER JOIN competencias c ON c.id = p.competencia_id
            LEFT JOIN areas_tecnicas a ON a.id = p.area_tecnica_id
            LEFT JOIN subareas_tecnicas s ON s.id = p.subarea_tecnica_id
            {where}
            ORDER BY COALESCE(p.ordem, 999999), p.id
            """,
            tuple(parametros)
        )

        registros = cursor.fetchall()

        return [
            _registro_para_pergunta(registro)
            for registro in registros
        ]

    finally:
        conexao.close()


def buscar_pergunta(pergunta_id: int) -> Pergunta | None:
    """Busca uma pergunta pelo ID sem esconder registros inativos."""
    _validar_id(pergunta_id, "ID da pergunta")

    conexao = conectar_banco()
    cursor = conexao.cursor()

    try:
        cursor.execute(
            """
            SELECT *
            FROM perguntas
            WHERE id = ?
            """,
            (pergunta_id,)
        )

        registro = cursor.fetchone()

        if registro is None:
            return None

        return _registro_para_pergunta(registro)

    finally:
        conexao.close()


def buscar_pergunta_ativa(pergunta_id: int) -> Pergunta | None:
    """Busca a pergunta somente quando ela e todos os registros relacionados estão ativos."""
    _validar_id(pergunta_id, "ID da pergunta")

    perguntas = listar_perguntas(somente_ativas=True)

    # A lista já possui todas as regras de disponibilidade aplicadas.
    for pergunta in perguntas:
        if pergunta.id == pergunta_id:
            return pergunta

    return None


def listar_perguntas_por_tipo(
    tipo_entrevista_id: int,
    somente_ativas: bool = True
) -> list[Pergunta]:
    """Lista perguntas vinculadas a um tipo de entrevista."""
    return listar_perguntas(
        somente_ativas=somente_ativas,
        tipo_entrevista_id=tipo_entrevista_id
    )


def listar_perguntas_por_competencia(
    competencia_id: int,
    somente_ativas: bool = True
) -> list[Pergunta]:
    """Lista perguntas vinculadas a uma competência."""
    return listar_perguntas(
        somente_ativas=somente_ativas,
        competencia_id=competencia_id
    )


def listar_perguntas_por_area(
    area_tecnica_id: int,
    somente_ativas: bool = True
) -> list[Pergunta]:
    """Lista perguntas vinculadas a uma área técnica."""
    return listar_perguntas(
        somente_ativas=somente_ativas,
        area_tecnica_id=area_tecnica_id
    )


def listar_perguntas_por_subarea(
    subarea_tecnica_id: int,
    somente_ativas: bool = True
) -> list[Pergunta]:
    """Lista perguntas vinculadas diretamente a uma subárea técnica."""
    return listar_perguntas(
        somente_ativas=somente_ativas,
        subarea_tecnica_id=subarea_tecnica_id
    )


def listar_perguntas_tecnicas(
    area_tecnica_id: int,
    subarea_tecnica_id: int,
    incluir_geral: bool = True
) -> list[Pergunta]:
    """Lista as perguntas técnicas da subárea escolhida e, quando pedido, também as da Geral."""
    _validar_id(area_tecnica_id, "Área técnica")
    _validar_id(subarea_tecnica_id, "Subárea técnica")

    conexao = conectar_banco()
    cursor = conexao.cursor()

    try:
        # A área precisa existir e estar ativa para participar de uma nova entrevista.
        area = _buscar_area_tecnica(cursor, area_tecnica_id)

        if area is None:
            raise ValueError("Área técnica não encontrada.")

        if not bool(area["ativo"]):
            raise ValueError("A área técnica selecionada está inativa.")

        # A subárea precisa existir, pertencer à área e estar ativa.
        subarea = _buscar_subarea_tecnica(cursor, subarea_tecnica_id)

        if subarea is None:
            raise ValueError("Subárea técnica não encontrada.")

        if subarea["area_tecnica_id"] != area_tecnica_id:
            raise ValueError("A subárea informada não pertence à área técnica selecionada.")

        if not bool(subarea["ativo"]):
            raise ValueError("A subárea técnica selecionada está inativa.")

        # Localiza a Geral da mesma área porque ela pode fazer parte da seleção.
        cursor.execute(
            """
            SELECT id
            FROM subareas_tecnicas
            WHERE area_tecnica_id = ?
              AND eh_geral = 1
              AND ativo = 1
            LIMIT 1
            """,
            (area_tecnica_id,)
        )

        geral = cursor.fetchone()

        if geral is None:
            raise ValueError("A área técnica não possui uma subárea Geral ativa.")

        geral_id = int(geral["id"])
        subareas_ids = [subarea_tecnica_id]

        # Quando a escolha já é Geral, ela não deve ser repetida na lista.
        if incluir_geral and subarea_tecnica_id != geral_id:
            subareas_ids.insert(0, geral_id)

        placeholders = ",".join("?" for _ in subareas_ids)
        parametros = [area_tecnica_id, *subareas_ids]

        cursor.execute(
            f"""
            SELECT p.*
            FROM perguntas p
            INNER JOIN tipos_entrevista te ON te.id = p.tipo_entrevista_id
            INNER JOIN competencias c ON c.id = p.competencia_id
            INNER JOIN areas_tecnicas a ON a.id = p.area_tecnica_id
            INNER JOIN subareas_tecnicas s ON s.id = p.subarea_tecnica_id
            WHERE p.ativa = 1
              AND te.ativo = 1
              AND te.usa_area_tecnica = 1
              AND c.ativa = 1
              AND a.ativo = 1
              AND s.ativo = 1
              AND p.area_tecnica_id = ?
              AND p.subarea_tecnica_id IN ({placeholders})
              AND s.area_tecnica_id = p.area_tecnica_id
            ORDER BY
                CASE
                    WHEN p.subarea_tecnica_id = {geral_id} THEN 0
                    ELSE 1
                END,
                COALESCE(p.ordem, 999999),
                p.id
            """,
            tuple(parametros)
        )

        registros = cursor.fetchall()

        return [
            _registro_para_pergunta(registro)
            for registro in registros
        ]

    finally:
        conexao.close()


def editar_pergunta(
    pergunta_id: int,
    pergunta: Pergunta
) -> bool:
    """Atualiza uma pergunta aplicando as mesmas regras usadas no cadastro."""
    _validar_id(pergunta_id, "ID da pergunta")
    _validar_campos_pergunta(pergunta)

    conexao = conectar_banco()
    cursor = conexao.cursor()

    try:
        # A existência, as referências e a alteração são verificadas dentro da mesma transação.
        cursor.execute("BEGIN IMMEDIATE")

        cursor.execute(
            """
            SELECT id
            FROM perguntas
            WHERE id = ?
            """,
            (pergunta_id,)
        )

        if cursor.fetchone() is None:
            conexao.rollback()
            return False

        _validar_referencias_pergunta(
            cursor,
            pergunta,
            exigir_ativos=True
        )

        exemplo_esperado = None

        if pergunta.exemplo_esperado is not None and pergunta.exemplo_esperado.strip():
            exemplo_esperado = pergunta.exemplo_esperado.strip()

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
                exemplo_esperado,
                pergunta.ordem,
                1 if pergunta.ativa else 0,
                pergunta.peso,
                1 if pergunta.usa_star else 0,
                pergunta.area_tecnica_id,
                pergunta.subarea_tecnica_id,
                pergunta_id
            )
        )

        conexao.commit()

        return True

    except (sqlite3.Error, ValueError):
        conexao.rollback()
        raise
    finally:
        conexao.close()


def desativar_pergunta(pergunta_id: int) -> bool:
    """Inativa uma pergunta sem apagar o registro histórico."""
    _validar_id(pergunta_id, "ID da pergunta")

    conexao = conectar_banco()
    cursor = conexao.cursor()

    try:
        cursor.execute(
            """
            UPDATE perguntas
            SET ativa = 0
            WHERE id = ?
            """,
            (pergunta_id,)
        )

        alterada = cursor.rowcount > 0

        conexao.commit()

        return alterada

    except sqlite3.Error:
        conexao.rollback()
        raise
    finally:
        conexao.close()


def reativar_pergunta(pergunta_id: int) -> bool:
    """Reativa uma pergunta somente quando todos os relacionamentos ainda estão válidos e ativos."""
    _validar_id(pergunta_id, "ID da pergunta")

    conexao = conectar_banco()
    cursor = conexao.cursor()

    try:
        cursor.execute("BEGIN IMMEDIATE")

        cursor.execute(
            """
            SELECT *
            FROM perguntas
            WHERE id = ?
            """,
            (pergunta_id,)
        )

        registro = cursor.fetchone()

        if registro is None:
            conexao.rollback()
            return False

        # Usa os dados já gravados para conferir novamente tipo, competência, área e subárea.
        pergunta = _registro_para_pergunta(registro)

        _validar_campos_pergunta(pergunta)

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
            (pergunta_id,)
        )

        conexao.commit()

        return True

    except (sqlite3.Error, ValueError):
        conexao.rollback()
        raise
    finally:
        conexao.close()


def excluir_pergunta(pergunta_id: int) -> bool:
    """Exclui fisicamente uma pergunta apenas quando ela nunca foi usada em uma entrevista."""
    _validar_id(pergunta_id, "ID da pergunta")

    conexao = conectar_banco()
    cursor = conexao.cursor()

    try:
        cursor.execute("BEGIN IMMEDIATE")

        # Primeiro confirma se a pergunta realmente existe.
        cursor.execute(
            """
            SELECT id
            FROM perguntas
            WHERE id = ?
            """,
            (pergunta_id,)
        )

        if cursor.fetchone() is None:
            conexao.rollback()
            return False

        # Perguntas já respondidas precisam continuar no banco para preservar o histórico.
        cursor.execute(
            """
            SELECT COUNT(*) AS quantidade
            FROM respostas
            WHERE pergunta_id = ?
            """,
            (pergunta_id,)
        )

        quantidade_respostas = int(cursor.fetchone()["quantidade"])

        if quantidade_respostas > 0:
            raise ValueError(
                "A pergunta não pode ser excluída porque já foi utilizada em uma entrevista. "
                "Utilize a opção de inativação."
            )

        # O conjunto congelado da entrevista também é considerado uso histórico.
        cursor.execute(
            """
            SELECT COUNT(*) AS quantidade
            FROM entrevista_perguntas
            WHERE pergunta_id = ?
            """,
            (pergunta_id,)
        )

        quantidade_snapshots = int(cursor.fetchone()["quantidade"])

        if quantidade_snapshots > 0:
            raise ValueError(
                "A pergunta não pode ser excluída porque faz parte do conjunto histórico de uma entrevista. "
                "Utilize a opção de inativação."
            )

        cursor.execute(
            """
            DELETE FROM perguntas
            WHERE id = ?
            """,
            (pergunta_id,)
        )

        conexao.commit()

        return True

    except (sqlite3.Error, ValueError):
        conexao.rollback()
        raise
    finally:
        conexao.close()


def _registro_para_pergunta(registro: sqlite3.Row) -> Pergunta:
    """Transforma uma linha do SQLite em um objeto Pergunta."""
    colunas = registro.keys()

    return Pergunta(
        id=registro["id"],
        tipo_entrevista_id=registro["tipo_entrevista_id"],
        competencia_id=registro["competencia_id"],
        texto=registro["texto"],
        exemplo_esperado=registro["exemplo_esperado"],
        ordem=registro["ordem"],
        ativa=bool(registro["ativa"]),
        peso=registro["peso"],
        usa_star=bool(registro["usa_star"]),
        data_criacao=registro["data_criacao"],
        area_tecnica_id=registro["area_tecnica_id"] if "area_tecnica_id" in colunas else None,
        subarea_tecnica_id=registro["subarea_tecnica_id"] if "subarea_tecnica_id" in colunas else None
    )