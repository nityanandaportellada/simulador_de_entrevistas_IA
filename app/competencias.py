"""Funções responsáveis pelo gerenciamento das competências do simulador."""

import sqlite3

try:
    from .database import conectar_banco
except ImportError:
    from database import conectar_banco

# Limites usados na validação dos dados recebidos pela camada de serviço.
TAMANHO_MAXIMO_NOME = 100
TAMANHO_MAXIMO_DESCRICAO = 1000


def _validar_id(competencia_id: int) -> None:
    """Valida se o ID da competência é um número inteiro maior que zero."""
    if not isinstance(competencia_id, int):
        raise ValueError("O ID da competência deve ser um número inteiro.")

    if competencia_id <= 0:
        raise ValueError("O ID da competência deve ser maior que zero.")


def _normalizar_nome(nome: str) -> str:
    """Remove espaços extras e valida o nome da competência."""
    if nome is None:
        raise ValueError("O nome da competência é obrigatório.")

    if not isinstance(nome, str):
        raise ValueError("O nome da competência deve ser um texto.")

    nome = nome.strip()

    if not nome:
        raise ValueError("O nome da competência não pode estar vazio.")

    if len(nome) > TAMANHO_MAXIMO_NOME:
        raise ValueError(
            "O nome da competência deve possuir no máximo "
            f"{TAMANHO_MAXIMO_NOME} caracteres."
        )

    return nome


def _normalizar_descricao(descricao: str | None) -> str | None:
    """Valida a descrição e transforma texto vazio em None."""
    if descricao is None:
        return None

    if not isinstance(descricao, str):
        raise ValueError("A descrição da competência deve ser um texto.")

    descricao = descricao.strip()

    if not descricao:
        return None

    if len(descricao) > TAMANHO_MAXIMO_DESCRICAO:
        raise ValueError(
            "A descrição da competência deve possuir no máximo "
            f"{TAMANHO_MAXIMO_DESCRICAO} caracteres."
        )

    return descricao


def _registro_para_dict(registro: sqlite3.Row) -> dict:
    """Converte uma linha do SQLite para o formato usado pela API."""
    # No banco a coluna se chama ativa, mas a API usa a chave ativo.
    return {
        "id": registro["id"],
        "nome": registro["nome"],
        "descricao": registro["descricao"],
        "ativo": bool(registro["ativa"])
    }


def nome_competencia_existe(nome: str, ignorar_id: int | None = None) -> bool:
    """Verifica se já existe outra competência com o mesmo nome."""
    nome = _normalizar_nome(nome)
    conexao = conectar_banco()
    cursor = conexao.cursor()

    try:
        if ignorar_id is None:
            cursor.execute(
                """
                SELECT id
                FROM competencias
                WHERE LOWER(nome) = LOWER(?)
                LIMIT 1
                """,
                (nome,)
            )
        else:
            # Na edição ignora o próprio registro na busca por duplicidade.
            _validar_id(ignorar_id)
            cursor.execute(
                """
                SELECT id
                FROM competencias
                WHERE LOWER(nome) = LOWER(?) AND id <> ?
                LIMIT 1
                """,
                (nome, ignorar_id)
            )

        return cursor.fetchone() is not None
    finally:
        conexao.close()


def cadastrar_competencia(nome: str, descricao: str | None = None) -> int:
    """Cadastra uma competência ativa e devolve o ID criado."""
    nome = _normalizar_nome(nome)
    descricao = _normalizar_descricao(descricao)

    if nome_competencia_existe(nome):
        raise ValueError("Já existe uma competência cadastrada com esse nome.")

    conexao = conectar_banco()
    cursor = conexao.cursor()

    try:
        cursor.execute(
            """
            INSERT INTO competencias (nome, descricao, ativa)
            VALUES (?, ?, 1)
            """,
            (nome, descricao)
        )

        competencia_id = cursor.lastrowid
        conexao.commit()
        return competencia_id
    except sqlite3.IntegrityError:
        # A restrição UNIQUE do banco também impede nomes repetidos.
        conexao.rollback()
        raise ValueError("Já existe uma competência cadastrada com esse nome.")
    except sqlite3.Error:
        conexao.rollback()
        raise
    finally:
        conexao.close()


def listar_competencias(somente_ativas: bool = False) -> list[dict]:
    """Lista as competências e permite retornar somente as competências ativas."""
    conexao = conectar_banco()
    cursor = conexao.cursor()

    try:
        if somente_ativas:
            cursor.execute(
                """
                SELECT id, nome, descricao, ativa
                FROM competencias
                WHERE ativa = 1
                ORDER BY nome COLLATE NOCASE, id
                """
            )
        else:
            cursor.execute(
                """
                SELECT id, nome, descricao, ativa
                FROM competencias
                ORDER BY nome COLLATE NOCASE, id
                """
            )

        competencias = []

        # Converte os registros encontrados para dicionários simples.
        for registro in cursor.fetchall():
            competencias.append(_registro_para_dict(registro))

        return competencias
    finally:
        conexao.close()


def buscar_competencia(competencia_id: int) -> dict | None:
    """Busca uma competência pelo ID e devolve None quando ela não existe."""
    _validar_id(competencia_id)
    conexao = conectar_banco()
    cursor = conexao.cursor()

    try:
        cursor.execute(
            """
            SELECT id, nome, descricao, ativa
            FROM competencias
            WHERE id = ?
            """,
            (competencia_id,)
        )

        registro = cursor.fetchone()

        if registro is None:
            return None

        return _registro_para_dict(registro)
    finally:
        conexao.close()


def editar_competencia(
    competencia_id: int,
    nome: str,
    descricao: str | None = None
) -> bool:
    """Atualiza o nome e a descrição de uma competência existente."""
    _validar_id(competencia_id)
    nome = _normalizar_nome(nome)
    competencia_atual = buscar_competencia(competencia_id)

    if competencia_atual is None:
        return False

    if nome_competencia_existe(nome, ignorar_id=competencia_id):
        raise ValueError("Já existe uma competência cadastrada com esse nome.")

    # Quando descricao é None, o comportamento atual do projeto preserva a descrição existente.
    if descricao is None:
        descricao_final = competencia_atual["descricao"]
    else:
        descricao_final = _normalizar_descricao(descricao)

    conexao = conectar_banco()
    cursor = conexao.cursor()

    try:
        cursor.execute(
            """
            UPDATE competencias
            SET nome = ?, descricao = ?
            WHERE id = ?
            """,
            (nome, descricao_final, competencia_id)
        )

        conexao.commit()
        return True
    except sqlite3.IntegrityError:
        conexao.rollback()
        raise ValueError("Já existe uma competência cadastrada com esse nome.")
    except sqlite3.Error:
        conexao.rollback()
        raise
    finally:
        conexao.close()


def contar_perguntas_competencia(competencia_id: int) -> int:
    """Conta todas as perguntas ligadas à competência, inclusive as inativas."""
    _validar_id(competencia_id)
    conexao = conectar_banco()
    cursor = conexao.cursor()

    try:
        cursor.execute(
            """
            SELECT COUNT(*) AS quantidade
            FROM perguntas
            WHERE competencia_id = ?
            """,
            (competencia_id,)
        )

        return int(cursor.fetchone()["quantidade"])
    finally:
        conexao.close()


def contar_perguntas_ativas_competencia(competencia_id: int) -> int:
    """Conta somente as perguntas ativas ligadas à competência."""
    _validar_id(competencia_id)
    conexao = conectar_banco()
    cursor = conexao.cursor()

    try:
        cursor.execute(
            """
            SELECT COUNT(*) AS quantidade
            FROM perguntas
            WHERE competencia_id = ? AND ativa = 1
            """,
            (competencia_id,)
        )

        return int(cursor.fetchone()["quantidade"])
    finally:
        conexao.close()


def competencia_em_uso(competencia_id: int) -> bool:
    """Informa se existe pelo menos uma pergunta vinculada à competência."""
    return contar_perguntas_competencia(competencia_id) > 0


def ativar_competencia(competencia_id: int) -> bool:
    """Ativa uma competência existente."""
    _validar_id(competencia_id)
    competencia = buscar_competencia(competencia_id)

    if competencia is None:
        return False

    if competencia["ativo"]:
        return True

    return _alterar_status_competencia(competencia_id, True)


def inativar_competencia(competencia_id: int) -> bool:
    """Inativa a competência somente quando ela não possui perguntas ativas."""
    _validar_id(competencia_id)
    competencia = buscar_competencia(competencia_id)

    if competencia is None:
        return False

    # Se já estiver inativa, nenhuma nova alteração é necessária.
    if not competencia["ativo"]:
        return True

    # Uma competência usada por pergunta ativa precisa continuar disponível.
    quantidade_perguntas_ativas = contar_perguntas_ativas_competencia(competencia_id)

    if quantidade_perguntas_ativas > 0:
        raise ValueError(
            "A competência não pode ser inativada porque "
            "possui perguntas ativas vinculadas."
        )

    return _alterar_status_competencia(competencia_id, False)


def _alterar_status_competencia(competencia_id: int, ativa: bool) -> bool:
    """Atualiza no banco o status ativo ou inativo da competência."""
    _validar_id(competencia_id)
    conexao = conectar_banco()
    cursor = conexao.cursor()

    try:
        cursor.execute(
            """
            UPDATE competencias
            SET ativa = ?
            WHERE id = ?
            """,
            (1 if ativa else 0, competencia_id)
        )

        conexao.commit()
        return cursor.rowcount > 0
    except sqlite3.Error:
        conexao.rollback()
        raise
    finally:
        conexao.close()


def obter_detalhes_competencia(competencia_id: int) -> dict | None:
    """Retorna a competência e informações sobre as perguntas ligadas a ela."""
    _validar_id(competencia_id)
    competencia = buscar_competencia(competencia_id)

    if competencia is None:
        return None

    # As duas contagens são usadas na administração para mostrar a utilização da competência.
    quantidade_perguntas = contar_perguntas_competencia(competencia_id)
    quantidade_perguntas_ativas = contar_perguntas_ativas_competencia(competencia_id)

    return {
        "id": competencia["id"],
        "nome": competencia["nome"],
        "descricao": competencia["descricao"],
        "ativo": competencia["ativo"],
        "quantidade_perguntas": quantidade_perguntas,
        "quantidade_perguntas_ativas": quantidade_perguntas_ativas,
        "em_uso": quantidade_perguntas > 0
    }