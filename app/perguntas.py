
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
    if valor is None or not isinstance(valor, int) or isinstance(valor, bool) or valor <= 0:
        raise ValueError(f"{campo} inválido.")


def _validar_campos_pergunta(pergunta: Pergunta) -> None:
    """Valida os campos básicos antes de verificar os relacionamentos."""
    _validar_id(pergunta.tipo_entrevista_id, "Tipo de entrevista")

    # A obrigatoriedade da competência será verificada conforme o tipo.
    if pergunta.competencia_id is not None:
        _validar_id(pergunta.competencia_id, "Competência")

    if not isinstance(pergunta.texto, str) or len(pergunta.texto.strip()) < 3:
        raise ValueError("O texto da pergunta deve possuir pelo menos 3 caracteres.")

    if pergunta.peso is None or pergunta.peso <= 0:
        raise ValueError("O peso da pergunta deve ser maior que zero.")

    if pergunta.ordem is not None and pergunta.ordem <= 0:
        raise ValueError("A ordem da pergunta deve ser maior que zero.")

    if pergunta.codigo is not None:
        if not isinstance(pergunta.codigo, str):
            raise ValueError("O código da pergunta deve ser um texto.")

        codigo = pergunta.codigo.strip()
        if len(codigo) < 3 or len(codigo) > 30:
            raise ValueError("O código da pergunta deve possuir entre 3 e 30 caracteres.")

    if pergunta.dificuldade is not None:
        if pergunta.dificuldade not in ("basica", "intermediaria", "avancada"):
            raise ValueError("A dificuldade deve ser basica, intermediaria ou avancada.")


def _buscar_tipo_entrevista(cursor: sqlite3.Cursor, tipo_entrevista_id: int):
    """Busca o tipo de entrevista utilizando a conexão atual."""
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
    """Busca uma competência cadastrada no banco."""
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
    """Valida o tipo, a competência e os vínculos técnicos da pergunta."""
    tipo = _buscar_tipo_entrevista(cursor, pergunta.tipo_entrevista_id)

    if tipo is None:
        raise ValueError("Tipo de entrevista não encontrado.")

    if exigir_ativos and not bool(tipo["ativo"]):
        raise ValueError("O tipo de entrevista informado está inativo.")

    usa_area_tecnica = bool(tipo["usa_area_tecnica"])

    # Perguntas não técnicas precisam possuir uma competência.
    # Perguntas técnicas podem não possuir competência comportamental.
    if pergunta.competencia_id is None:
        if not usa_area_tecnica:
            raise ValueError("A competência é obrigatória para este tipo de entrevista.")
    else:
        _validar_id(pergunta.competencia_id, "Competência")
        competencia = _buscar_competencia(cursor, pergunta.competencia_id)

        if competencia is None:
            raise ValueError("Competência não encontrada.")

        if exigir_ativos and not bool(competencia["ativa"]):
            raise ValueError("A competência informada está inativa.")

    # A configuração do tipo define se área e subárea são exigidas.
    if usa_area_tecnica:
        if pergunta.area_tecnica_id is None:
            raise ValueError("A área técnica é obrigatória para este tipo de entrevista.")

        if pergunta.subarea_tecnica_id is None:
            raise ValueError("A subárea técnica é obrigatória para este tipo de entrevista.")

        _validar_id(pergunta.area_tecnica_id, "Área técnica")
        _validar_id(pergunta.subarea_tecnica_id, "Subárea técnica")

        area = _buscar_area_tecnica(cursor, pergunta.area_tecnica_id)

        if area is None:
            raise ValueError("Área técnica não encontrada.")

        if exigir_ativos and not bool(area["ativo"]):
            raise ValueError("A área técnica informada está inativa.")

        subarea = _buscar_subarea_tecnica(cursor, pergunta.subarea_tecnica_id)

        if subarea is None:
            raise ValueError("Subárea técnica não encontrada.")

        if subarea["area_tecnica_id"] != pergunta.area_tecnica_id:
            raise ValueError("A subárea informada não pertence à área técnica selecionada.")

        if exigir_ativos and not bool(subarea["ativo"]):
            raise ValueError("A subárea técnica informada está inativa.")
    else:
        if pergunta.area_tecnica_id is not None or pergunta.subarea_tecnica_id is not None:
            raise ValueError("Este tipo de entrevista não utiliza área ou subárea técnica.")


def validar_pergunta(pergunta: Pergunta) -> None:
    """Executa as validações dos campos e relacionamentos da pergunta."""
    _validar_campos_pergunta(pergunta)
    conexao = conectar_banco()

    try:
        _validar_referencias_pergunta(conexao.cursor(), pergunta, exigir_ativos=True)
    finally:
        conexao.close()


def cadastrar_pergunta(pergunta: Pergunta) -> int:
    """Cadastra uma pergunta após validar seus dados na mesma transação."""
    _validar_campos_pergunta(pergunta)
    conexao = conectar_banco()
    cursor = conexao.cursor()

    try:
        cursor.execute("BEGIN IMMEDIATE")
        _validar_referencias_pergunta(cursor, pergunta, exigir_ativos=True)

        exemplo_esperado = None
        if pergunta.exemplo_esperado is not None and pergunta.exemplo_esperado.strip():
            exemplo_esperado = pergunta.exemplo_esperado.strip()

        codigo = pergunta.codigo.strip() if pergunta.codigo is not None else None

        cursor.execute(
            """
            INSERT INTO perguntas (
                tipo_entrevista_id,
                competencia_id,
                texto,
                exemplo_esperado,
                codigo,
                dificuldade,
                ordem,
                ativa,
                peso,
                usa_star,
                area_tecnica_id,
                subarea_tecnica_id
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                pergunta.tipo_entrevista_id,
                pergunta.competencia_id,
                pergunta.texto.strip(),
                exemplo_esperado,
                codigo,
                pergunta.dificuldade,
                pergunta.ordem,
                1 if pergunta.ativa else 0,
                pergunta.peso,
                1 if pergunta.usa_star else 0,
                pergunta.area_tecnica_id,
                pergunta.subarea_tecnica_id
            )
        )

        pergunta_id = int(cursor.lastrowid)
        conexao.commit()
        return pergunta_id

    except sqlite3.IntegrityError as erro:
        conexao.rollback()
        if "perguntas.codigo" in str(erro) or "idx_perguntas_codigo" in str(erro):
            raise ValueError("Já existe uma pergunta cadastrada com este código.") from erro
        raise
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

        if somente_ativas:
            condicoes.append("p.ativa = 1")
            condicoes.append("te.ativo = 1")

            # A competência pode ser nula somente quando o tipo usa área técnica.
            condicoes.append(
                """
                (
                    (te.usa_area_tecnica = 1 AND (p.competencia_id IS NULL OR c.ativa = 1))
                    OR (te.usa_area_tecnica = 0 AND p.competencia_id IS NOT NULL AND c.ativa = 1)
                )
                """
            )

            condicoes.append(
                """
                (
                    (
                        te.usa_area_tecnica = 0
                        AND p.area_tecnica_id IS NULL
                        AND p.subarea_tecnica_id IS NULL
                    )
                    OR (
                        te.usa_area_tecnica = 1
                        AND p.area_tecnica_id IS NOT NULL
                        AND p.subarea_tecnica_id IS NOT NULL
                        AND a.ativo = 1
                        AND s.ativo = 1
                        AND s.area_tecnica_id = p.area_tecnica_id
                    )
                )
                """
            )

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
            LEFT JOIN competencias c ON c.id = p.competencia_id
            LEFT JOIN areas_tecnicas a ON a.id = p.area_tecnica_id
            LEFT JOIN subareas_tecnicas s ON s.id = p.subarea_tecnica_id
            {where}
            ORDER BY COALESCE(p.ordem, 999999), p.id
            """,
            tuple(parametros)
        )

        registros = cursor.fetchall()
        return [_registro_para_pergunta(registro) for registro in registros]
    finally:
        conexao.close()


def buscar_pergunta(pergunta_id: int) -> Pergunta | None:
    """Busca uma pergunta pelo ID, inclusive quando ela está inativa."""
    _validar_id(pergunta_id, "ID da pergunta")
    conexao = conectar_banco()
    cursor = conexao.cursor()

    try:
        cursor.execute("SELECT * FROM perguntas WHERE id = ?", (pergunta_id,))
        registro = cursor.fetchone()

        if registro is None:
            return None

        return _registro_para_pergunta(registro)
    finally:
        conexao.close()


def buscar_pergunta_ativa(pergunta_id: int) -> Pergunta | None:
    """Busca uma pergunta disponível, respeitando os vínculos ativos."""
    _validar_id(pergunta_id, "ID da pergunta")
    perguntas = listar_perguntas(somente_ativas=True)

    for pergunta in perguntas:
        if pergunta.id == pergunta_id:
            return pergunta

    return None


def listar_perguntas_por_tipo(
    tipo_entrevista_id: int,
    somente_ativas: bool = True
) -> list[Pergunta]:
    """Lista perguntas vinculadas a determinado tipo de entrevista."""
    return listar_perguntas(
        somente_ativas=somente_ativas,
        tipo_entrevista_id=tipo_entrevista_id
    )


def listar_perguntas_por_competencia(
    competencia_id: int,
    somente_ativas: bool = True
) -> list[Pergunta]:
    """Lista perguntas vinculadas a determinada competência."""
    return listar_perguntas(
        somente_ativas=somente_ativas,
        competencia_id=competencia_id
    )


def listar_perguntas_por_area(
    area_tecnica_id: int,
    somente_ativas: bool = True
) -> list[Pergunta]:
    """Lista perguntas cadastradas em uma área técnica."""
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
    """Lista perguntas da subárea escolhida e, opcionalmente, da subárea Geral."""
    _validar_id(area_tecnica_id, "Área técnica")
    _validar_id(subarea_tecnica_id, "Subárea técnica")
    conexao = conectar_banco()
    cursor = conexao.cursor()

    try:
        area = _buscar_area_tecnica(cursor, area_tecnica_id)

        if area is None:
            raise ValueError("Área técnica não encontrada.")

        if not bool(area["ativo"]):
            raise ValueError("A área técnica selecionada está inativa.")

        subarea = _buscar_subarea_tecnica(cursor, subarea_tecnica_id)

        if subarea is None:
            raise ValueError("Subárea técnica não encontrada.")

        if subarea["area_tecnica_id"] != area_tecnica_id:
            raise ValueError("A subárea informada não pertence à área técnica selecionada.")

        if not bool(subarea["ativo"]):
            raise ValueError("A subárea técnica selecionada está inativa.")

        # Localiza a subárea Geral da mesma área.
        cursor.execute(
            """
            SELECT id
            FROM subareas_tecnicas
            WHERE area_tecnica_id = ? AND eh_geral = 1 AND ativo = 1
            LIMIT 1
            """,
            (area_tecnica_id,)
        )
        geral = cursor.fetchone()

        if geral is None:
            raise ValueError("A área técnica não possui uma subárea Geral ativa.")

        geral_id = int(geral["id"])
        subareas_ids = [subarea_tecnica_id]

        if incluir_geral and subarea_tecnica_id != geral_id:
            subareas_ids.insert(0, geral_id)

        placeholders = ",".join("?" for _ in subareas_ids)
        parametros = [area_tecnica_id, *subareas_ids]

        cursor.execute(
            f"""
            SELECT p.*
            FROM perguntas p
            INNER JOIN tipos_entrevista te ON te.id = p.tipo_entrevista_id
            LEFT JOIN competencias c ON c.id = p.competencia_id
            INNER JOIN areas_tecnicas a ON a.id = p.area_tecnica_id
            INNER JOIN subareas_tecnicas s ON s.id = p.subarea_tecnica_id
            WHERE p.ativa = 1
              AND te.ativo = 1
              AND te.usa_area_tecnica = 1
              AND (p.competencia_id IS NULL OR c.ativa = 1)
              AND a.ativo = 1
              AND s.ativo = 1
              AND p.area_tecnica_id = ?
              AND p.subarea_tecnica_id IN ({placeholders})
              AND s.area_tecnica_id = p.area_tecnica_id
            ORDER BY
                CASE WHEN p.subarea_tecnica_id = ? THEN 0 ELSE 1 END,
                COALESCE(p.ordem, 999999),
                p.id
            """,
            tuple(parametros + [geral_id])
        )

        registros = cursor.fetchall()
        return [_registro_para_pergunta(registro) for registro in registros]
    finally:
        conexao.close()


def editar_pergunta(pergunta_id: int, pergunta: Pergunta) -> bool:
    """Atualiza uma pergunta utilizando as mesmas validações do cadastro."""
    _validar_id(pergunta_id, "ID da pergunta")
    _validar_campos_pergunta(pergunta)
    conexao = conectar_banco()
    cursor = conexao.cursor()

    try:
        cursor.execute("BEGIN IMMEDIATE")
        cursor.execute("SELECT id FROM perguntas WHERE id = ?", (pergunta_id,))

        if cursor.fetchone() is None:
            conexao.rollback()
            return False

        _validar_referencias_pergunta(cursor, pergunta, exigir_ativos=True)

        exemplo_esperado = None
        if pergunta.exemplo_esperado is not None and pergunta.exemplo_esperado.strip():
            exemplo_esperado = pergunta.exemplo_esperado.strip()

        codigo = pergunta.codigo.strip() if pergunta.codigo is not None else None

        cursor.execute(
            """
            UPDATE perguntas
            SET tipo_entrevista_id = ?,
                competencia_id = ?,
                texto = ?,
                exemplo_esperado = ?,
                codigo = ?,
                dificuldade = ?,
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
                codigo,
                pergunta.dificuldade,
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

    except sqlite3.IntegrityError as erro:
        conexao.rollback()
        if "perguntas.codigo" in str(erro) or "idx_perguntas_codigo" in str(erro):
            raise ValueError("Já existe uma pergunta cadastrada com este código.") from erro
        raise
    except (sqlite3.Error, ValueError):
        conexao.rollback()
        raise
    finally:
        conexao.close()


def desativar_pergunta(pergunta_id: int) -> bool:
    """Inativa uma pergunta sem apagar seu registro histórico."""
    _validar_id(pergunta_id, "ID da pergunta")
    conexao = conectar_banco()
    cursor = conexao.cursor()

    try:
        cursor.execute(
            "UPDATE perguntas SET ativa = 0 WHERE id = ?",
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
    """Reativa uma pergunta somente quando seus relacionamentos estão válidos."""
    _validar_id(pergunta_id, "ID da pergunta")
    conexao = conectar_banco()
    cursor = conexao.cursor()

    try:
        cursor.execute("BEGIN IMMEDIATE")
        cursor.execute("SELECT * FROM perguntas WHERE id = ?", (pergunta_id,))
        registro = cursor.fetchone()

        if registro is None:
            conexao.rollback()
            return False

        pergunta = _registro_para_pergunta(registro)
        _validar_campos_pergunta(pergunta)
        _validar_referencias_pergunta(cursor, pergunta, exigir_ativos=True)

        cursor.execute(
            "UPDATE perguntas SET ativa = 1 WHERE id = ?",
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
    """Exclui uma pergunta somente quando ela não possui utilização histórica."""
    _validar_id(pergunta_id, "ID da pergunta")
    conexao = conectar_banco()
    cursor = conexao.cursor()

    try:
        cursor.execute("BEGIN IMMEDIATE")
        cursor.execute("SELECT id FROM perguntas WHERE id = ?", (pergunta_id,))

        if cursor.fetchone() is None:
            conexao.rollback()
            return False

        # Impede exclusão de perguntas que possuem respostas.
        cursor.execute(
            "SELECT COUNT(*) AS quantidade FROM respostas WHERE pergunta_id = ?",
            (pergunta_id,)
        )
        quantidade_respostas = int(cursor.fetchone()["quantidade"])

        if quantidade_respostas > 0:
            raise ValueError(
                "A pergunta não pode ser excluída porque já foi utilizada em uma entrevista. "
                "Utilize a opção de inativação."
            )

        # Também impede exclusão quando a pergunta foi congelada em uma entrevista.
        cursor.execute(
            "SELECT COUNT(*) AS quantidade FROM entrevista_perguntas WHERE pergunta_id = ?",
            (pergunta_id,)
        )
        quantidade_snapshots = int(cursor.fetchone()["quantidade"])

        if quantidade_snapshots > 0:
            raise ValueError(
                "A pergunta não pode ser excluída porque faz parte do conjunto histórico de uma entrevista. "
                "Utilize a opção de inativação."
            )

        cursor.execute("DELETE FROM perguntas WHERE id = ?", (pergunta_id,))
        conexao.commit()
        return True

    except (sqlite3.Error, ValueError):
        conexao.rollback()
        raise
    finally:
        conexao.close()


def _registro_para_pergunta(registro: sqlite3.Row) -> Pergunta:
    """Converte uma linha do banco de dados para um objeto Pergunta."""
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
        subarea_tecnica_id=registro["subarea_tecnica_id"] if "subarea_tecnica_id" in colunas else None,
        codigo=registro["codigo"] if "codigo" in colunas else None,
        dificuldade=registro["dificuldade"] if "dificuldade" in colunas else None
    )
