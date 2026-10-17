"""Funções responsáveis pelo gerenciamento das áreas técnicas do simulador."""

import sqlite3

try:
    from .database import conectar_banco
    from .models import AreaTecnica
except ImportError:
    from database import conectar_banco
    from models import AreaTecnica


def _registro_para_area(registro) -> AreaTecnica:
    """Transforma uma linha do SQLite em um objeto AreaTecnica."""
    return AreaTecnica(
        id=registro["id"],
        nome=registro["nome"],
        descricao=registro["descricao"],
        ativo=bool(registro["ativo"]),
        ordem=registro["ordem"],
        data_criacao=registro["data_criacao"]
    )


def _validar_id(valor: int, campo: str) -> None:
    """Confere se o identificador informado existe e é maior que zero."""
    if valor is None or valor <= 0:
        raise ValueError(f"{campo} inválido.")


def _validar_nome(nome: str) -> str:
    """Remove espaços extras e valida o tamanho do nome da área."""
    if nome is None:
        raise ValueError("O nome da área é obrigatório.")

    nome = nome.strip()

    if len(nome) < 2:
        raise ValueError("O nome da área deve possuir pelo menos 2 caracteres.")

    if len(nome) > 150:
        raise ValueError("O nome da área deve possuir no máximo 150 caracteres.")

    return nome


def _validar_ordem(ordem: int | None) -> None:
    """Impede o uso de uma ordem de exibição negativa."""
    if ordem is not None and ordem < 0:
        raise ValueError("A ordem não pode ser negativa.")


def _nome_duplicado(cursor, nome: str, ignorar_id: int | None = None) -> bool:
    """Verifica se já existe outra área cadastrada com o mesmo nome."""
    if ignorar_id is None:
        cursor.execute(
            """
            SELECT id
            FROM areas_tecnicas
            WHERE LOWER(nome) = LOWER(?)
            LIMIT 1
            """,
            (nome,)
        )
    else:
        cursor.execute(
            """
            SELECT id
            FROM areas_tecnicas
            WHERE LOWER(nome) = LOWER(?) AND id <> ?
            LIMIT 1
            """,
            (nome, ignorar_id)
        )

    return cursor.fetchone() is not None


def buscar_area_tecnica(area_id: int) -> AreaTecnica | None:
    """Busca uma área técnica pelo ID e devolve None quando ela não existe."""
    _validar_id(area_id, "ID da área")
    conexao = conectar_banco()
    cursor = conexao.cursor()

    try:
        cursor.execute(
            """
            SELECT id, nome, descricao, ativo, ordem, data_criacao
            FROM areas_tecnicas
            WHERE id = ?
            """,
            (area_id,)
        )
        registro = cursor.fetchone()

        if registro is None:
            return None

        return _registro_para_area(registro)
    finally:
        conexao.close()


def listar_areas_tecnicas(somente_ativas: bool = True) -> list[AreaTecnica]:
    """Lista as áreas cadastradas e permite filtrar somente as áreas ativas."""
    conexao = conectar_banco()
    cursor = conexao.cursor()

    try:
        if somente_ativas:
            cursor.execute(
                """
                SELECT id, nome, descricao, ativo, ordem, data_criacao
                FROM areas_tecnicas
                WHERE ativo = 1
                ORDER BY COALESCE(ordem, 999999), nome, id
                """
            )
        else:
            cursor.execute(
                """
                SELECT id, nome, descricao, ativo, ordem, data_criacao
                FROM areas_tecnicas
                ORDER BY COALESCE(ordem, 999999), nome, id
                """
            )

        registros = cursor.fetchall()
        return [_registro_para_area(registro) for registro in registros]
    finally:
        conexao.close()


def cadastrar_area_tecnica(area: AreaTecnica) -> int:
    """Cadastra uma área e cria automaticamente a subárea protegida Geral."""
    nome = _validar_nome(area.nome)
    _validar_ordem(area.ordem)
    descricao = area.descricao

    # Textos vazios são gravados como NULL no banco.
    if descricao is not None:
        descricao = descricao.strip() or None

    conexao = conectar_banco()
    cursor = conexao.cursor()

    try:
        # A área e a subárea Geral precisam ser criadas na mesma transação.
        cursor.execute("BEGIN IMMEDIATE")

        if _nome_duplicado(cursor, nome):
            raise ValueError("Já existe uma área técnica com este nome.")

        cursor.execute(
            """
            INSERT INTO areas_tecnicas (nome, descricao, ativo, ordem)
            VALUES (?, ?, 1, ?)
            """,
            (nome, descricao, area.ordem)
        )
        area_id = cursor.lastrowid

        # Toda nova área recebe uma subárea Geral para perguntas comuns da área.
        cursor.execute(
            """
            INSERT INTO subareas_tecnicas (
                area_tecnica_id, nome, descricao, eh_geral, ativo, ordem
            )
            VALUES (?, 'Geral', ?, 1, 1, 1)
            """,
            (area_id, "Subárea padrão destinada a perguntas gerais da área.")
        )

        conexao.commit()
        return int(area_id)
    except (sqlite3.Error, ValueError):
        conexao.rollback()
        raise
    finally:
        conexao.close()


def editar_area_tecnica(area_id: int, area: AreaTecnica) -> bool:
    """Atualiza nome, descrição e ordem de uma área sem mudar seu status."""
    _validar_id(area_id, "ID da área")
    nome = _validar_nome(area.nome)
    _validar_ordem(area.ordem)
    descricao = area.descricao

    if descricao is not None:
        descricao = descricao.strip() or None

    conexao = conectar_banco()
    cursor = conexao.cursor()

    try:
        # A verificação e a alteração são feitas juntas para evitar conflito de escrita.
        cursor.execute("BEGIN IMMEDIATE")
        cursor.execute("SELECT id FROM areas_tecnicas WHERE id = ?", (area_id,))

        if cursor.fetchone() is None:
            conexao.rollback()
            return False

        if _nome_duplicado(cursor, nome, area_id):
            raise ValueError("Já existe outra área técnica com este nome.")

        cursor.execute(
            """
            UPDATE areas_tecnicas
            SET nome = ?, descricao = ?, ordem = ?
            WHERE id = ?
            """,
            (nome, descricao, area.ordem, area_id)
        )

        conexao.commit()
        return True
    except (sqlite3.Error, ValueError):
        conexao.rollback()
        raise
    finally:
        conexao.close()


def contar_perguntas_ativas_area(area_id: int) -> int:
    """Conta perguntas ativas ligadas diretamente à área ou às suas subáreas."""
    _validar_id(area_id, "ID da área")
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
                    OR p.subarea_tecnica_id IN (
                        SELECT s.id
                        FROM subareas_tecnicas s
                        WHERE s.area_tecnica_id = ?
                    )
              )
            """,
            (area_id, area_id)
        )

        return int(cursor.fetchone()["quantidade"])
    finally:
        conexao.close()


def inativar_area_tecnica(area_id: int) -> bool:
    """Inativa uma área somente quando não existem perguntas ativas vinculadas a ela."""
    _validar_id(area_id, "ID da área")
    conexao = conectar_banco()
    cursor = conexao.cursor()

    try:
        cursor.execute("BEGIN IMMEDIATE")
        cursor.execute(
            """
            SELECT id, ativo
            FROM areas_tecnicas
            WHERE id = ?
            """,
            (area_id,)
        )
        registro = cursor.fetchone()

        if registro is None:
            conexao.rollback()
            return False

        # Uma área já inativa não precisa ser alterada novamente.
        if not bool(registro["ativo"]):
            conexao.commit()
            return True

        # A consulta considera perguntas da própria área e de qualquer subárea dela.
        cursor.execute(
            """
            SELECT COUNT(*) AS quantidade
            FROM perguntas p
            WHERE p.ativa = 1
              AND (
                    p.area_tecnica_id = ?
                    OR p.subarea_tecnica_id IN (
                        SELECT s.id
                        FROM subareas_tecnicas s
                        WHERE s.area_tecnica_id = ?
                    )
              )
            """,
            (area_id, area_id)
        )
        quantidade = int(cursor.fetchone()["quantidade"])

        if quantidade > 0:
            raise ValueError("A área não pode ser inativada porque possui perguntas ativas vinculadas.")

        cursor.execute("UPDATE areas_tecnicas SET ativo = 0 WHERE id = ?", (area_id,))
        conexao.commit()
        return True
    except (sqlite3.Error, ValueError):
        conexao.rollback()
        raise
    finally:
        conexao.close()


def ativar_area_tecnica(area_id: int) -> bool:
    """Ativa uma área existente e garante que sua subárea Geral esteja cadastrada."""
    _validar_id(area_id, "ID da área")
    conexao = conectar_banco()
    cursor = conexao.cursor()

    try:
        cursor.execute("BEGIN IMMEDIATE")
        cursor.execute("SELECT id FROM areas_tecnicas WHERE id = ?", (area_id,))

        if cursor.fetchone() is None:
            conexao.rollback()
            return False

        # Bancos antigos podem não possuir a subárea Geral, por isso ela é conferida aqui.
        cursor.execute(
            """
            SELECT id
            FROM subareas_tecnicas
            WHERE area_tecnica_id = ? AND eh_geral = 1
            LIMIT 1
            """,
            (area_id,)
        )
        geral = cursor.fetchone()

        if geral is None:
            cursor.execute(
                """
                INSERT INTO subareas_tecnicas (
                    area_tecnica_id, nome, descricao, eh_geral, ativo, ordem
                )
                VALUES (?, 'Geral', ?, 1, 1, 1)
                """,
                (area_id, "Subárea padrão destinada a perguntas gerais da área.")
            )

        cursor.execute("UPDATE areas_tecnicas SET ativo = 1 WHERE id = ?", (area_id,))
        conexao.commit()
        return True
    except sqlite3.Error:
        conexao.rollback()
        raise
    finally:
        conexao.close()