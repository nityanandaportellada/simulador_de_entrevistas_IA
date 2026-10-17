"""Funções responsáveis pelo cadastro e gerenciamento dos usuários."""

import sqlite3
from datetime import datetime

try:
    from .database import conectar_banco
    from .models import Usuario
except ImportError:
    from database import conectar_banco
    from models import Usuario

# Perfis que podem ser gravados na tabela de usuários.
PERFIS_PERMITIDOS = ("estudante", "administrador")


class AdministradorJaExisteError(ValueError):
    """Indica que o primeiro administrador já foi criado e o bootstrap não pode ser repetido."""
    pass


def normalizar_email(email: str) -> str:
    """Remove espaços do e-mail e converte o texto para letras minúsculas."""
    # O e-mail precisa existir e precisa ser um texto.
    if email is None:
        raise ValueError("O e-mail é obrigatório.")

    if not isinstance(email, str):
        raise ValueError("O e-mail deve ser um texto.")

    # A normalização evita diferenças causadas por espaços ou letras maiúsculas.
    email = email.strip().lower()

    if not email:
        raise ValueError("O e-mail é obrigatório.")

    return email


def _validar_nome(nome: str) -> str:
    """Valida o nome do usuário e devolve o texto sem espaços nas extremidades."""
    if nome is None:
        raise ValueError("O nome é obrigatório.")

    if not isinstance(nome, str):
        raise ValueError("O nome deve ser um texto.")

    nome = nome.strip()

    if not nome:
        raise ValueError("O nome é obrigatório.")

    return nome


def _validar_usuario_id(usuario_id: int) -> None:
    """Verifica se o ID informado é um número inteiro maior que zero."""
    if not isinstance(usuario_id, int):
        raise ValueError("O ID do usuário deve ser um número inteiro.")

    if usuario_id <= 0:
        raise ValueError("O ID do usuário é inválido.")


def email_existe(email: str, ignorar_usuario_id: int | None = None) -> bool:
    """Verifica se um e-mail já está cadastrado, podendo ignorar um usuário durante a edição."""
    email = normalizar_email(email)
    conexao = conectar_banco()
    cursor = conexao.cursor()

    try:
        # No cadastro é necessário procurar o e-mail em todos os usuários.
        if ignorar_usuario_id is None:
            cursor.execute(
                """
                SELECT 1
                FROM usuarios
                WHERE LOWER(email) = LOWER(?)
                LIMIT 1
                """,
                (email,)
            )
        else:
            # Na edição o próprio usuário deve ser ignorado na verificação.
            _validar_usuario_id(ignorar_usuario_id)

            cursor.execute(
                """
                SELECT 1
                FROM usuarios
                WHERE LOWER(email) = LOWER(?) AND id <> ?
                LIMIT 1
                """,
                (email, ignorar_usuario_id)
            )

        return cursor.fetchone() is not None

    finally:
        conexao.close()


def administrador_existe() -> bool:
    """Verifica se já existe algum administrador, mesmo que ele esteja inativo."""
    conexao = conectar_banco()
    cursor = conexao.cursor()

    try:
        # Administradores inativos também contam para impedir um novo bootstrap.
        cursor.execute(
            """
            SELECT 1
            FROM usuarios
            WHERE perfil = 'administrador'
            LIMIT 1
            """
        )

        return cursor.fetchone() is not None

    finally:
        conexao.close()


def contar_administradores_ativos() -> int:
    """Retorna quantos administradores estão ativos no sistema."""
    conexao = conectar_banco()
    cursor = conexao.cursor()

    try:
        cursor.execute(
            """
            SELECT COUNT(*) AS quantidade
            FROM usuarios
            WHERE perfil = 'administrador' AND ativo = 1
            """
        )

        registro = cursor.fetchone()
        return int(registro["quantidade"])

    finally:
        conexao.close()


def cadastrar_usuario(
    nome: str,
    email: str,
    senha_hash: str,
    perfil: str = "estudante"
) -> int:
    """Cadastra um usuário com a senha já transformada em hash e devolve o novo ID."""
    # Valida os dados antes de abrir a operação de gravação.
    nome = _validar_nome(nome)
    email = normalizar_email(email)

    if not senha_hash:
        raise ValueError("O hash da senha é obrigatório.")

    if perfil not in PERFIS_PERMITIDOS:
        raise ValueError("Perfil de usuário inválido.")

    if email_existe(email):
        raise ValueError("Já existe um usuário cadastrado com este e-mail.")

    conexao = conectar_banco()
    cursor = conexao.cursor()

    try:
        # Grava o usuário como ativo. A senha em texto puro nunca chega a esta função.
        cursor.execute(
            """
            INSERT INTO usuarios (nome, email, senha_hash, perfil, ativo)
            VALUES (?, ?, ?, ?, 1)
            """,
            (nome, email, senha_hash, perfil)
        )

        usuario_id = cursor.lastrowid
        conexao.commit()

        return usuario_id

    except sqlite3.IntegrityError as erro:
        # A restrição UNIQUE do banco também protege contra e-mails duplicados.
        conexao.rollback()

        raise ValueError(
            "Não foi possível cadastrar o usuário. "
            "Verifique se o e-mail já está cadastrado."
        ) from erro

    except sqlite3.Error:
        conexao.rollback()
        raise

    finally:
        conexao.close()


def cadastrar_primeiro_administrador(
    nome: str,
    email: str,
    senha_hash: str
) -> int:
    """Cria o primeiro administrador somente quando ainda não existe outro administrador."""
    nome = _validar_nome(nome)
    email = normalizar_email(email)

    if not senha_hash:
        raise ValueError("O hash da senha é obrigatório.")

    conexao = conectar_banco()
    cursor = conexao.cursor()

    try:
        # BEGIN IMMEDIATE reserva a escrita enquanto a verificação e o cadastro são feitos.
        # Isso evita que duas requisições criem dois primeiros administradores ao mesmo tempo.
        cursor.execute("BEGIN IMMEDIATE")

        # Confere novamente dentro da mesma transação se já existe administrador.
        cursor.execute(
            """
            SELECT 1
            FROM usuarios
            WHERE perfil = 'administrador'
            LIMIT 1
            """
        )

        if cursor.fetchone() is not None:
            raise AdministradorJaExisteError(
                "Já existe um administrador cadastrado. "
                "O bootstrap administrativo está desabilitado."
            )

        # O e-mail também precisa estar livre, mesmo que pertença a um estudante.
        cursor.execute(
            """
            SELECT 1
            FROM usuarios
            WHERE LOWER(email) = LOWER(?)
            LIMIT 1
            """,
            (email,)
        )

        if cursor.fetchone() is not None:
            raise ValueError(
                "Já existe um usuário cadastrado com este e-mail."
            )

        # Cria o primeiro administrador já ativo.
        cursor.execute(
            """
            INSERT INTO usuarios (nome, email, senha_hash, perfil, ativo)
            VALUES (?, ?, ?, 'administrador', 1)
            """,
            (nome, email, senha_hash)
        )

        usuario_id = cursor.lastrowid
        conexao.commit()

        return usuario_id

    except (AdministradorJaExisteError, ValueError):
        conexao.rollback()
        raise

    except sqlite3.IntegrityError as erro:
        conexao.rollback()

        raise ValueError(
            "Não foi possível cadastrar o primeiro administrador."
        ) from erro

    except sqlite3.Error:
        conexao.rollback()
        raise

    finally:
        conexao.close()


def buscar_usuario(usuario_id: int) -> Usuario | None:
    """Busca um usuário pelo ID e devolve None quando ele não existe."""
    _validar_usuario_id(usuario_id)
    conexao = conectar_banco()
    cursor = conexao.cursor()

    try:
        cursor.execute(
            "SELECT * FROM usuarios WHERE id = ?",
            (usuario_id,)
        )

        registro = cursor.fetchone()

        if registro is None:
            return None

        return _registro_para_usuario(registro)

    finally:
        conexao.close()


def buscar_usuario_por_email(email: str) -> Usuario | None:
    """Busca um usuário pelo e-mail e devolve None quando não encontra o cadastro."""
    email = normalizar_email(email)
    conexao = conectar_banco()
    cursor = conexao.cursor()

    try:
        cursor.execute(
            "SELECT * FROM usuarios WHERE LOWER(email) = LOWER(?)",
            (email,)
        )

        registro = cursor.fetchone()

        if registro is None:
            return None

        return _registro_para_usuario(registro)

    finally:
        conexao.close()


def listar_usuarios(somente_ativos: bool = False) -> list[Usuario]:
    """Lista os usuários e permite retornar somente os que estão ativos."""
    conexao = conectar_banco()
    cursor = conexao.cursor()

    try:
        if somente_ativos:
            cursor.execute(
                "SELECT * FROM usuarios WHERE ativo = 1 ORDER BY nome, id"
            )
        else:
            cursor.execute(
                "SELECT * FROM usuarios ORDER BY nome, id"
            )

        registros = cursor.fetchall()
        usuarios = []

        # Converte cada linha do SQLite em um objeto Usuario.
        for registro in registros:
            usuarios.append(_registro_para_usuario(registro))

        return usuarios

    finally:
        conexao.close()


def atualizar_usuario(
    usuario_id: int,
    nome: str,
    email: str
) -> bool:
    """Atualiza somente o nome e o e-mail de um usuário já cadastrado."""
    _validar_usuario_id(usuario_id)
    nome = _validar_nome(nome)
    email = normalizar_email(email)

    # Antes de atualizar, confirma que o usuário existe e que o novo e-mail está disponível.
    usuario = buscar_usuario(usuario_id)

    if usuario is None:
        raise ValueError("Usuário não encontrado.")

    if email_existe(email, ignorar_usuario_id=usuario_id):
        raise ValueError(
            "Já existe outro usuário cadastrado com este e-mail."
        )

    conexao = conectar_banco()
    cursor = conexao.cursor()

    try:
        cursor.execute(
            "UPDATE usuarios SET nome = ?, email = ? WHERE id = ?",
            (nome, email, usuario_id)
        )

        conexao.commit()
        return cursor.rowcount > 0

    except sqlite3.IntegrityError as erro:
        conexao.rollback()

        raise ValueError(
            "O e-mail informado já está cadastrado."
        ) from erro

    except sqlite3.Error:
        conexao.rollback()
        raise

    finally:
        conexao.close()


def atualizar_senha_hash(usuario_id: int, senha_hash: str) -> bool:
    """Substitui o hash da senha de um usuário sem receber a senha em texto puro."""
    _validar_usuario_id(usuario_id)

    if not senha_hash:
        raise ValueError("O hash da senha é obrigatório.")

    conexao = conectar_banco()
    cursor = conexao.cursor()

    try:
        cursor.execute(
            "UPDATE usuarios SET senha_hash = ? WHERE id = ?",
            (senha_hash, usuario_id)
        )

        conexao.commit()
        return cursor.rowcount > 0

    except sqlite3.Error:
        conexao.rollback()
        raise

    finally:
        conexao.close()


def alterar_perfil(usuario_id: int, perfil: str) -> bool:
    """Altera o perfil e impede que o sistema fique sem nenhum administrador ativo."""
    _validar_usuario_id(usuario_id)

    if perfil not in PERFIS_PERMITIDOS:
        raise ValueError("Perfil de usuário inválido.")

    conexao = conectar_banco()
    cursor = conexao.cursor()

    try:
        # A transação mantém juntas a verificação dos administradores e a alteração do perfil.
        cursor.execute("BEGIN IMMEDIATE")

        cursor.execute(
            "SELECT id, perfil, ativo FROM usuarios WHERE id = ?",
            (usuario_id,)
        )

        usuario = cursor.fetchone()

        if usuario is None:
            conexao.rollback()
            return False

        perfil_atual = usuario["perfil"]
        usuario_ativo = bool(usuario["ativo"])

        # Se for o último administrador ativo, ele deve continuar administrador.
        if (
            perfil_atual == "administrador"
            and usuario_ativo
            and perfil != "administrador"
        ):
            cursor.execute(
                """
                SELECT COUNT(*) AS quantidade
                FROM usuarios
                WHERE perfil = 'administrador' AND ativo = 1
                """
            )

            quantidade = int(cursor.fetchone()["quantidade"])

            if quantidade <= 1:
                raise ValueError(
                    "O último administrador ativo não pode perder "
                    "o perfil de administrador."
                )

        cursor.execute(
            "UPDATE usuarios SET perfil = ? WHERE id = ?",
            (perfil, usuario_id)
        )

        conexao.commit()
        return True

    except (ValueError, sqlite3.Error):
        conexao.rollback()
        raise

    finally:
        conexao.close()


def ativar_usuario(usuario_id: int) -> bool:
    """Ativa um usuário existente e devolve False quando o ID não é encontrado."""
    _validar_usuario_id(usuario_id)
    conexao = conectar_banco()
    cursor = conexao.cursor()

    try:
        # Primeiro confirma a existência do cadastro.
        cursor.execute(
            "SELECT id FROM usuarios WHERE id = ?",
            (usuario_id,)
        )

        if cursor.fetchone() is None:
            return False

        cursor.execute(
            "UPDATE usuarios SET ativo = 1 WHERE id = ?",
            (usuario_id,)
        )

        conexao.commit()
        return True

    except sqlite3.Error:
        conexao.rollback()
        raise

    finally:
        conexao.close()


def inativar_usuario(usuario_id: int) -> bool:
    """Inativa um usuário sem excluí-lo e protege o último administrador ativo."""
    _validar_usuario_id(usuario_id)
    conexao = conectar_banco()
    cursor = conexao.cursor()

    try:
        # Mantém a consulta e a alteração na mesma transação para evitar conflito entre requisições.
        cursor.execute("BEGIN IMMEDIATE")

        cursor.execute(
            "SELECT id, perfil, ativo FROM usuarios WHERE id = ?",
            (usuario_id,)
        )

        usuario = cursor.fetchone()

        if usuario is None:
            conexao.rollback()
            return False

        usuario_ativo = bool(usuario["ativo"])
        perfil = usuario["perfil"]

        # Se já estiver inativo, não é necessário alterar nada.
        if not usuario_ativo:
            conexao.commit()
            return True

        # Um administrador só pode ser inativado quando existir outro administrador ativo.
        if perfil == "administrador":
            cursor.execute(
                """
                SELECT COUNT(*) AS quantidade
                FROM usuarios
                WHERE perfil = 'administrador' AND ativo = 1
                """
            )

            quantidade = int(cursor.fetchone()["quantidade"])

            if quantidade <= 1:
                raise ValueError(
                    "O último administrador ativo não pode ser inativado."
                )

        cursor.execute(
            "UPDATE usuarios SET ativo = 0 WHERE id = ?",
            (usuario_id,)
        )

        conexao.commit()
        return True

    except (ValueError, sqlite3.Error):
        conexao.rollback()
        raise

    finally:
        conexao.close()


def registrar_ultimo_acesso(usuario_id: int) -> None:
    """Atualiza a data e a hora do último login realizado com sucesso."""
    _validar_usuario_id(usuario_id)

    # Mantém o mesmo formato de data já usado pelo projeto.
    data = datetime.now().isoformat(
        sep=" ",
        timespec="seconds"
    )

    conexao = conectar_banco()
    cursor = conexao.cursor()

    try:
        cursor.execute(
            "UPDATE usuarios SET ultimo_acesso = ? WHERE id = ?",
            (data, usuario_id)
        )

        conexao.commit()

    except sqlite3.Error:
        conexao.rollback()
        raise

    finally:
        conexao.close()


def _registro_para_usuario(registro: sqlite3.Row) -> Usuario:
    """Transforma uma linha recebida do SQLite em um objeto Usuario."""
    return Usuario(
        id=registro["id"],
        nome=registro["nome"],
        email=registro["email"],
        senha_hash=registro["senha_hash"],
        perfil=registro["perfil"],
        ativo=bool(registro["ativo"]),
        data_criacao=registro["data_criacao"],
        ultimo_acesso=registro["ultimo_acesso"]
    )