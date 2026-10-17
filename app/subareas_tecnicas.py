"""Funções responsáveis pelo gerenciamento das subáreas técnicas do simulador."""

import sqlite3

try:
    from .database import conectar_banco
    from .models import SubareaTecnica
except ImportError:
    from database import conectar_banco
    from models import SubareaTecnica


def _registro_para_subarea(registro) -> SubareaTecnica:
    """Transforma uma linha do SQLite em um objeto SubareaTecnica."""
    return SubareaTecnica(
        id=registro["id"],
        area_tecnica_id=registro["area_tecnica_id"],
        nome=registro["nome"],
        descricao=registro["descricao"],
        eh_geral=bool(registro["eh_geral"]),
        ativo=bool(registro["ativo"]),
        ordem=registro["ordem"],
        data_criacao=registro["data_criacao"]
    )


def _validar_id(valor: int, campo: str) -> None:
    """Confere se o identificador informado existe e é maior que zero."""
    if valor is None or valor <= 0:
        raise ValueError(f"{campo} inválido.")


def _validar_nome(nome: str) -> str:
    """Valida o nome da subárea e impede a criação manual da opção Geral."""
    if nome is None:
        raise ValueError("O nome da subárea é obrigatório.")

    nome = nome.strip()

    if len(nome) < 2:
        raise ValueError("O nome da subárea deve possuir pelo menos 2 caracteres.")

    if len(nome) > 150:
        raise ValueError("O nome da subárea deve possuir no máximo 150 caracteres.")

    # A subárea Geral é reservada e é criada automaticamente pelo sistema.
    if nome.casefold() == "geral":
        raise ValueError("A subárea Geral é criada automaticamente pelo sistema.")

    return nome


def _validar_ordem(ordem: int | None) -> None:
    """Impede o uso de uma ordem de exibição negativa."""
    if ordem is not None and ordem < 0:
        raise ValueError("A ordem não pode ser negativa.")


def _buscar_area(cursor, area_id: int):
    """Busca uma área usando a mesma conexão da operação atual."""
    cursor.execute(
        """
        SELECT id, nome, ativo
        FROM areas_tecnicas
        WHERE id = ?
        """,
        (area_id,)
    )
    return cursor.fetchone()


def _nome_duplicado(
    cursor,
    area_id: int,
    nome: str,
    ignorar_id: int | None = None
) -> bool:
    """Verifica se a mesma área já possui outra subárea com o nome informado."""
    if ignorar_id is None:
        cursor.execute(
            """
            SELECT id
            FROM subareas_tecnicas
            WHERE area_tecnica_id = ? AND LOWER(nome) = LOWER(?)
            LIMIT 1
            """,
            (area_id, nome)
        )
    else:
        cursor.execute(
            """
            SELECT id
            FROM subareas_tecnicas
            WHERE area_tecnica_id = ? AND LOWER(nome) = LOWER(?) AND id <> ?
            LIMIT 1
            """,
            (area_id, nome, ignorar_id)
        )

    return cursor.fetchone() is not None


def buscar_subarea_tecnica(subarea_id: int) -> SubareaTecnica | None:
    """Busca uma subárea pelo ID e devolve None quando ela não existe."""
    _validar_id(subarea_id, "ID da subárea")
    conexao = conectar_banco()
    cursor = conexao.cursor()

    try:
        cursor.execute(
            """
            SELECT id, area_tecnica_id, nome, descricao, eh_geral, ativo, ordem, data_criacao
            FROM subareas_tecnicas
            WHERE id = ?
            """,
            (subarea_id,)
        )
        registro = cursor.fetchone()

        if registro is None:
            return None

        return _registro_para_subarea(registro)
    finally:
        conexao.close()


def listar_subareas_tecnicas(
    area_tecnica_id: int | None = None,
    somente_ativas: bool = True
) -> list[SubareaTecnica]:
    """Lista subáreas e permite filtrar por área e por status ativo."""
    conexao = conectar_banco()
    cursor = conexao.cursor()

    try:
        parametros = []
        condicoes = []

        if area_tecnica_id is not None:
            _validar_id(area_tecnica_id, "ID da área")
            condicoes.append("area_tecnica_id = ?")
            parametros.append(area_tecnica_id)

        if somente_ativas:
            condicoes.append("ativo = 1")

        where = ""

        if condicoes:
            where = "WHERE " + " AND ".join(condicoes)

        cursor.execute(
            f"""
            SELECT id, area_tecnica_id, nome, descricao, eh_geral, ativo, ordem, data_criacao
            FROM subareas_tecnicas
            {where}
            ORDER BY area_tecnica_id, eh_geral DESC, COALESCE(ordem, 999999), nome, id
            """,
            tuple(parametros)
        )
        registros = cursor.fetchall()
        return [_registro_para_subarea(registro) for registro in registros]
    finally:
        conexao.close()


def cadastrar_subarea_tecnica(subarea: SubareaTecnica) -> int:
    """Cadastra uma subárea comum em uma área técnica ativa."""
    if subarea.area_tecnica_id is None:
        raise ValueError("A área técnica é obrigatória.")

    _validar_id(subarea.area_tecnica_id, "ID da área")
    nome = _validar_nome(subarea.nome)
    _validar_ordem(subarea.ordem)
    descricao = subarea.descricao

    if descricao is not None:
        descricao = descricao.strip() or None

    conexao = conectar_banco()
    cursor = conexao.cursor()

    try:
        # A validação da área e o cadastro são feitos na mesma transação.
        cursor.execute("BEGIN IMMEDIATE")
        area = _buscar_area(cursor, subarea.area_tecnica_id)

        if area is None:
            raise ValueError("Área técnica não encontrada.")

        if not bool(area["ativo"]):
            raise ValueError("Não é possível cadastrar uma subárea em uma área inativa.")

        if _nome_duplicado(cursor, subarea.area_tecnica_id, nome):
            raise ValueError("Já existe uma subárea com este nome nesta área.")

        cursor.execute(
            """
            INSERT INTO subareas_tecnicas (
                area_tecnica_id, nome, descricao, eh_geral, ativo, ordem
            )
            VALUES (?, ?, ?, 0, 1, ?)
            """,
            (subarea.area_tecnica_id, nome, descricao, subarea.ordem)
        )
        subarea_id = cursor.lastrowid

        conexao.commit()
        return int(subarea_id)
    except (sqlite3.Error, ValueError):
        conexao.rollback()
        raise
    finally:
        conexao.close()


def editar_subarea_tecnica(
    subarea_id: int,
    nome: str,
    descricao: str | None = None,
    ordem: int | None = None
) -> bool:
    """Edita uma subárea comum sem permitir alteração da subárea protegida Geral."""
    _validar_id(subarea_id, "ID da subárea")
    nome = _validar_nome(nome)
    _validar_ordem(ordem)

    if descricao is not None:
        descricao = descricao.strip() or None

    conexao = conectar_banco()
    cursor = conexao.cursor()

    try:
        cursor.execute("BEGIN IMMEDIATE")
        cursor.execute(
            """
            SELECT id, area_tecnica_id, eh_geral
            FROM subareas_tecnicas
            WHERE id = ?
            """,
            (subarea_id,)
        )
        atual = cursor.fetchone()

        if atual is None:
            conexao.rollback()
            return False

        # Geral é criada pelo sistema e não pode ser modificada manualmente.
        if bool(atual["eh_geral"]):
            raise ValueError("A subárea Geral não pode ser editada.")

        if _nome_duplicado(cursor, atual["area_tecnica_id"], nome, subarea_id):
            raise ValueError("Já existe outra subárea com este nome nesta área.")

        cursor.execute(
            """
            UPDATE subareas_tecnicas
            SET nome = ?, descricao = ?, ordem = ?
            WHERE id = ?
            """,
            (nome, descricao, ordem, subarea_id)
        )

        conexao.commit()
        return True
    except (sqlite3.Error, ValueError):
        conexao.rollback()
        raise
    finally:
        conexao.close()


def contar_perguntas_ativas_subarea(subarea_id: int) -> int:
    """Conta quantas perguntas ativas estão ligadas diretamente à subárea."""
    _validar_id(subarea_id, "ID da subárea")
    conexao = conectar_banco()
    cursor = conexao.cursor()

    try:
        cursor.execute(
            """
            SELECT COUNT(*) AS quantidade
            FROM perguntas
            WHERE subarea_tecnica_id = ? AND ativa = 1
            """,
            (subarea_id,)
        )
        return int(cursor.fetchone()["quantidade"])
    finally:
        conexao.close()


def inativar_subarea_tecnica(subarea_id: int) -> bool:
    """Inativa uma subárea comum quando ela não possui perguntas ativas."""
    _validar_id(subarea_id, "ID da subárea")
    conexao = conectar_banco()
    cursor = conexao.cursor()

    try:
        cursor.execute("BEGIN IMMEDIATE")
        cursor.execute(
            """
            SELECT id, eh_geral, ativo
            FROM subareas_tecnicas
            WHERE id = ?
            """,
            (subarea_id,)
        )
        registro = cursor.fetchone()

        if registro is None:
            conexao.rollback()
            return False

        if bool(registro["eh_geral"]):
            raise ValueError("A subárea Geral não pode ser inativada.")

        if not bool(registro["ativo"]):
            conexao.commit()
            return True

        # Subáreas usadas por perguntas ativas precisam continuar disponíveis.
        cursor.execute(
            """
            SELECT COUNT(*) AS quantidade
            FROM perguntas
            WHERE subarea_tecnica_id = ? AND ativa = 1
            """,
            (subarea_id,)
        )
        quantidade = int(cursor.fetchone()["quantidade"])

        if quantidade > 0:
            raise ValueError("A subárea não pode ser inativada porque possui perguntas ativas vinculadas.")

        cursor.execute("UPDATE subareas_tecnicas SET ativo = 0 WHERE id = ?", (subarea_id,))
        conexao.commit()
        return True
    except (sqlite3.Error, ValueError):
        conexao.rollback()
        raise
    finally:
        conexao.close()


def ativar_subarea_tecnica(subarea_id: int) -> bool:
    """Ativa uma subárea somente quando a área pai também está ativa."""
    _validar_id(subarea_id, "ID da subárea")
    conexao = conectar_banco()
    cursor = conexao.cursor()

    try:
        cursor.execute("BEGIN IMMEDIATE")
        cursor.execute(
            """
            SELECT s.id, s.area_tecnica_id, a.ativo AS area_ativa
            FROM subareas_tecnicas s
            INNER JOIN areas_tecnicas a ON a.id = s.area_tecnica_id
            WHERE s.id = ?
            """,
            (subarea_id,)
        )
        registro = cursor.fetchone()

        if registro is None:
            conexao.rollback()
            return False

        # Uma subárea não deve ficar disponível quando sua área está inativa.
        if not bool(registro["area_ativa"]):
            raise ValueError("A subárea não pode ser ativada enquanto a área técnica estiver inativa.")

        cursor.execute("UPDATE subareas_tecnicas SET ativo = 1 WHERE id = ?", (subarea_id,))
        conexao.commit()
        return True
    except (sqlite3.Error, ValueError):
        conexao.rollback()
        raise
    finally:
        conexao.close()


def validar_subarea_da_area(
    area_tecnica_id: int,
    subarea_tecnica_id: int,
    exigir_ativos: bool = True
) -> SubareaTecnica:
    """Confere se a subárea pertence à área informada e, quando pedido, se ambas estão ativas."""
    _validar_id(area_tecnica_id, "ID da área")
    _validar_id(subarea_tecnica_id, "ID da subárea")
    conexao = conectar_banco()
    cursor = conexao.cursor()

    try:
        cursor.execute(
            """
            SELECT
                s.id, s.area_tecnica_id, s.nome, s.descricao, s.eh_geral,
                s.ativo, s.ordem, s.data_criacao, a.ativo AS area_ativa
            FROM subareas_tecnicas s
            INNER JOIN areas_tecnicas a ON a.id = s.area_tecnica_id
            WHERE s.id = ? AND s.area_tecnica_id = ?
            """,
            (subarea_tecnica_id, area_tecnica_id)
        )
        registro = cursor.fetchone()

        if registro is None:
            raise ValueError("A subárea informada não pertence à área técnica selecionada.")

        if exigir_ativos:
            if not bool(registro["area_ativa"]):
                raise ValueError("A área técnica selecionada está inativa.")

            if not bool(registro["ativo"]):
                raise ValueError("A subárea técnica selecionada está inativa.")

        return _registro_para_subarea(registro)
    finally:
        conexao.close()