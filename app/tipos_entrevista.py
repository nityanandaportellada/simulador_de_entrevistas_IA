"""Funções responsáveis pelo gerenciamento dos tipos de entrevista."""

import sqlite3

try:
    from .database import conectar_banco
except ImportError:
    from database import conectar_banco

# Limite usado para evitar nomes muito grandes no cadastro.
TAMANHO_MAXIMO_NOME = 100


def _validar_id(tipo_entrevista_id: int) -> None:
    """Valida se o ID do tipo de entrevista é um número inteiro maior que zero."""
    if not isinstance(tipo_entrevista_id, int):
        raise ValueError("O ID do tipo de entrevista deve ser um número inteiro.")

    if tipo_entrevista_id <= 0:
        raise ValueError("O ID do tipo de entrevista deve ser maior que zero.")


def _normalizar_nome(nome: str) -> str:
    """Remove espaços extras e valida o nome informado para o tipo de entrevista."""
    if nome is None:
        raise ValueError("O nome do tipo de entrevista é obrigatório.")

    if not isinstance(nome, str):
        raise ValueError("O nome do tipo de entrevista deve ser um texto.")

    nome = nome.strip()

    if not nome:
        raise ValueError("O nome do tipo de entrevista não pode estar vazio.")

    if len(nome) > TAMANHO_MAXIMO_NOME:
        raise ValueError(
            "O nome do tipo de entrevista deve possuir "
            f"no máximo {TAMANHO_MAXIMO_NOME} caracteres."
        )

    return nome


def _registro_para_dict(registro: sqlite3.Row) -> dict:
    """Converte uma linha do SQLite no dicionário usado pelo restante do sistema."""
    return {
        "id": registro["id"],
        "nome": registro["nome"],
        "ativo": bool(registro["ativo"]),
        "usa_area_tecnica": bool(registro["usa_area_tecnica"])
    }


def nome_tipo_entrevista_existe(nome: str, ignorar_id: int | None = None) -> bool:
    """Verifica se já existe outro tipo de entrevista com o mesmo nome."""
    nome = _normalizar_nome(nome)
    conexao = conectar_banco()
    cursor = conexao.cursor()

    try:
        # No cadastro é feita a busca pelo nome em todos os registros.
        if ignorar_id is None:
            cursor.execute(
                """
                SELECT id
                FROM tipos_entrevista
                WHERE LOWER(nome) = LOWER(?)
                LIMIT 1
                """,
                (nome,)
            )
        else:
            # Na edição o próprio registro precisa ser ignorado na comparação.
            _validar_id(ignorar_id)
            cursor.execute(
                """
                SELECT id
                FROM tipos_entrevista
                WHERE LOWER(nome) = LOWER(?) AND id <> ?
                LIMIT 1
                """,
                (nome, ignorar_id)
            )

        return cursor.fetchone() is not None
    finally:
        conexao.close()


def cadastrar_tipo_entrevista(nome: str) -> int:
    """Cadastra um novo tipo de entrevista ativo e devolve o ID criado."""
    nome = _normalizar_nome(nome)

    # Evita cadastrar o mesmo nome duas vezes.
    if nome_tipo_entrevista_existe(nome):
        raise ValueError("Já existe um tipo de entrevista cadastrado com esse nome.")

    conexao = conectar_banco()
    cursor = conexao.cursor()

    try:
        cursor.execute(
            """
            INSERT INTO tipos_entrevista (nome, ativo)
            VALUES (?, 1)
            """,
            (nome,)
        )

        tipo_entrevista_id = cursor.lastrowid
        conexao.commit()
        return tipo_entrevista_id
    except sqlite3.IntegrityError:
        # A restrição UNIQUE do banco também protege contra nomes repetidos.
        conexao.rollback()
        raise ValueError("Já existe um tipo de entrevista cadastrado com esse nome.")
    except sqlite3.Error:
        conexao.rollback()
        raise
    finally:
        conexao.close()


def listar_tipos_entrevista(somente_ativos: bool = False) -> list[dict]:
    """Lista os tipos de entrevista e permite retornar somente os tipos ativos."""
    conexao = conectar_banco()
    cursor = conexao.cursor()

    try:
        if somente_ativos:
            cursor.execute(
                """
                SELECT id, nome, ativo, usa_area_tecnica
                FROM tipos_entrevista
                WHERE ativo = 1
                ORDER BY nome COLLATE NOCASE, id
                """
            )
        else:
            cursor.execute(
                """
                SELECT id, nome, ativo, usa_area_tecnica
                FROM tipos_entrevista
                ORDER BY nome COLLATE NOCASE, id
                """
            )

        tipos = []

        # Converte cada linha encontrada para o formato usado pela API.
        for registro in cursor.fetchall():
            tipos.append(_registro_para_dict(registro))

        return tipos
    finally:
        conexao.close()


def buscar_tipo_entrevista(tipo_entrevista_id: int) -> dict | None:
    """Busca um tipo de entrevista pelo ID e devolve None quando ele não existe."""
    _validar_id(tipo_entrevista_id)
    conexao = conectar_banco()
    cursor = conexao.cursor()

    try:
        cursor.execute(
            """
            SELECT id, nome, ativo, usa_area_tecnica
            FROM tipos_entrevista
            WHERE id = ?
            """,
            (tipo_entrevista_id,)
        )

        registro = cursor.fetchone()

        if registro is None:
            return None

        return _registro_para_dict(registro)
    finally:
        conexao.close()


def editar_tipo_entrevista(tipo_entrevista_id: int, nome: str) -> bool:
    """Atualiza o nome de um tipo de entrevista existente."""
    _validar_id(tipo_entrevista_id)
    nome = _normalizar_nome(nome)

    # Antes de editar, confirma se o tipo realmente existe.
    tipo_atual = buscar_tipo_entrevista(tipo_entrevista_id)

    if tipo_atual is None:
        return False

    # O novo nome não pode ser usado por outro tipo.
    if nome_tipo_entrevista_existe(nome, ignorar_id=tipo_entrevista_id):
        raise ValueError("Já existe um tipo de entrevista cadastrado com esse nome.")

    conexao = conectar_banco()
    cursor = conexao.cursor()

    try:
        cursor.execute(
            """
            UPDATE tipos_entrevista
            SET nome = ?
            WHERE id = ?
            """,
            (nome, tipo_entrevista_id)
        )

        conexao.commit()
        return True
    except sqlite3.IntegrityError:
        conexao.rollback()
        raise ValueError("Já existe um tipo de entrevista cadastrado com esse nome.")
    except sqlite3.Error:
        conexao.rollback()
        raise
    finally:
        conexao.close()


def contar_perguntas_tipo(tipo_entrevista_id: int) -> int:
    """Conta todas as perguntas vinculadas ao tipo, incluindo as perguntas inativas."""
    _validar_id(tipo_entrevista_id)
    conexao = conectar_banco()
    cursor = conexao.cursor()

    try:
        cursor.execute(
            """
            SELECT COUNT(*) AS quantidade
            FROM perguntas
            WHERE tipo_entrevista_id = ?
            """,
            (tipo_entrevista_id,)
        )

        return int(cursor.fetchone()["quantidade"])
    finally:
        conexao.close()


def contar_perguntas_ativas_tipo(tipo_entrevista_id: int) -> int:
    """Conta somente as perguntas ativas vinculadas ao tipo de entrevista."""
    _validar_id(tipo_entrevista_id)
    conexao = conectar_banco()
    cursor = conexao.cursor()

    try:
        cursor.execute(
            """
            SELECT COUNT(*) AS quantidade
            FROM perguntas
            WHERE tipo_entrevista_id = ? AND ativa = 1
            """,
            (tipo_entrevista_id,)
        )

        return int(cursor.fetchone()["quantidade"])
    finally:
        conexao.close()


def contar_entrevistas_tipo(tipo_entrevista_id: int) -> int:
    """Conta quantas entrevistas históricas estão ligadas ao tipo informado."""
    _validar_id(tipo_entrevista_id)
    conexao = conectar_banco()
    cursor = conexao.cursor()

    try:
        cursor.execute(
            """
            SELECT COUNT(*) AS quantidade
            FROM entrevistas
            WHERE tipo_entrevista_id = ?
            """,
            (tipo_entrevista_id,)
        )

        return int(cursor.fetchone()["quantidade"])
    finally:
        conexao.close()


def tipo_entrevista_em_uso(tipo_entrevista_id: int) -> bool:
    """Informa se o tipo possui perguntas ou entrevistas relacionadas."""
    quantidade_perguntas = contar_perguntas_tipo(tipo_entrevista_id)
    quantidade_entrevistas = contar_entrevistas_tipo(tipo_entrevista_id)
    return quantidade_perguntas > 0 or quantidade_entrevistas > 0


def ativar_tipo_entrevista(tipo_entrevista_id: int) -> bool:
    """Ativa um tipo de entrevista existente."""
    _validar_id(tipo_entrevista_id)
    tipo = buscar_tipo_entrevista(tipo_entrevista_id)

    if tipo is None:
        return False

    # Se já estiver ativo, a operação pode ser considerada concluída.
    if tipo["ativo"]:
        return True

    return _alterar_status_tipo_entrevista(tipo_entrevista_id, True)


def inativar_tipo_entrevista(tipo_entrevista_id: int) -> bool:
    """Inativa o tipo somente quando ele não possui perguntas ativas vinculadas."""
    _validar_id(tipo_entrevista_id)
    tipo = buscar_tipo_entrevista(tipo_entrevista_id)

    if tipo is None:
        return False

    # Não precisa alterar novamente um tipo que já está inativo.
    if not tipo["ativo"]:
        return True

    # Perguntas ativas impedem a inativação porque ainda poderiam ser usadas em novas entrevistas.
    quantidade_perguntas_ativas = contar_perguntas_ativas_tipo(tipo_entrevista_id)

    if quantidade_perguntas_ativas > 0:
        raise ValueError(
            "O tipo de entrevista não pode ser inativado "
            "porque possui perguntas ativas vinculadas."
        )

    return _alterar_status_tipo_entrevista(tipo_entrevista_id, False)


def _alterar_status_tipo_entrevista(tipo_entrevista_id: int, ativo: bool) -> bool:
    """Atualiza no banco o campo que informa se o tipo está ativo ou inativo."""
    _validar_id(tipo_entrevista_id)
    conexao = conectar_banco()
    cursor = conexao.cursor()

    try:
        cursor.execute(
            """
            UPDATE tipos_entrevista
            SET ativo = ?
            WHERE id = ?
            """,
            (1 if ativo else 0, tipo_entrevista_id)
        )

        conexao.commit()
        return cursor.rowcount > 0
    except sqlite3.Error:
        conexao.rollback()
        raise
    finally:
        conexao.close()


def obter_detalhes_tipo_entrevista(tipo_entrevista_id: int) -> dict | None:
    """Retorna o tipo e as quantidades de perguntas e entrevistas relacionadas a ele."""
    _validar_id(tipo_entrevista_id)
    tipo = buscar_tipo_entrevista(tipo_entrevista_id)

    if tipo is None:
        return None

    # Essas contagens ajudam a tela administrativa a mostrar se o tipo já está em uso.
    quantidade_perguntas = contar_perguntas_tipo(tipo_entrevista_id)
    quantidade_perguntas_ativas = contar_perguntas_ativas_tipo(tipo_entrevista_id)
    quantidade_entrevistas = contar_entrevistas_tipo(tipo_entrevista_id)

    return {
        "id": tipo["id"],
        "nome": tipo["nome"],
        "ativo": tipo["ativo"],
        "usa_area_tecnica": tipo["usa_area_tecnica"],
        "quantidade_perguntas": quantidade_perguntas,
        "quantidade_perguntas_ativas": quantidade_perguntas_ativas,
        "quantidade_entrevistas": quantidade_entrevistas,
        "em_uso": quantidade_perguntas > 0 or quantidade_entrevistas > 0
    }