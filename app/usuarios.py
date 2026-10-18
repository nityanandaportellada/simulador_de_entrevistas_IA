
"""Cadastro e gerenciamento de usuários com operações SQLite transacionais."""

import sqlite3
from datetime import datetime, timezone

try:
    from .database import conectar_banco
    from .models import Usuario
except ImportError:
    from database import conectar_banco
    from models import Usuario

PERFIS_PERMITIDOS = ("estudante", "administrador")


class AdministradorJaExisteError(ValueError):
    """Indica que o cadastro do primeiro administrador já foi realizado."""
    pass


def normalizar_email(email: str) -> str:
    """Remove espaços e padroniza o e-mail para evitar duplicações."""
    if not isinstance(email, str):
        raise ValueError("O e-mail deve ser um texto.")
    email = email.strip().lower()
    if not email or len(email) > 254 or email.count("@") != 1 or any(c.isspace() for c in email):
        raise ValueError("E-mail inválido.")
    return email


def _validar_nome(nome: str) -> str:
    """Confere tamanho e caracteres do nome antes de salvar."""
    if not isinstance(nome, str):
        raise ValueError("O nome deve ser um texto.")
    nome = nome.strip()
    if not 2 <= len(nome) <= 150 or not nome.isprintable():
        raise ValueError("O nome deve ter entre 2 e 150 caracteres válidos.")
    return nome


def _validar_usuario_id(usuario_id: int) -> None:
    """Impede identificadores negativos, zero e valores não inteiros."""
    if type(usuario_id) is not int or usuario_id <= 0:
        raise ValueError("ID de usuário inválido.")


def _validar_hash(senha_hash: str) -> None:
    """Rejeita hashes vazios ou valores que não sejam texto."""
    if not isinstance(senha_hash, str) or not senha_hash.strip():
        raise ValueError("O hash da senha é obrigatório.")


def _email_em_uso(cursor: sqlite3.Cursor, email: str, ignorar_id: int | None = None) -> bool:
    """Verifica duplicidade usando a própria conexão da transação."""
    if ignorar_id is None:
        cursor.execute("SELECT 1 FROM usuarios WHERE LOWER(email) = ? LIMIT 1", (email,))
    else:
        cursor.execute("SELECT 1 FROM usuarios WHERE LOWER(email) = ? AND id <> ? LIMIT 1", (email, ignorar_id))
    return cursor.fetchone() is not None


def email_existe(email: str, ignorar_usuario_id: int | None = None) -> bool:
    """Consulta a existência de um e-mail sem alterar o banco."""
    email = normalizar_email(email)
    if ignorar_usuario_id is not None:
        _validar_usuario_id(ignorar_usuario_id)
    conexao = conectar_banco()
    try:
        return _email_em_uso(conexao.cursor(), email, ignorar_usuario_id)
    finally:
        conexao.close()


def administrador_existe() -> bool:
    """Considera também administradores inativos para impedir novo bootstrap."""
    conexao = conectar_banco()
    try:
        return conexao.execute("SELECT 1 FROM usuarios WHERE perfil = 'administrador' LIMIT 1").fetchone() is not None
    finally:
        conexao.close()


def contar_administradores_ativos() -> int:
    """Conta os administradores com acesso habilitado."""
    conexao = conectar_banco()
    try:
        return int(conexao.execute("SELECT COUNT(*) FROM usuarios WHERE perfil = 'administrador' AND ativo = 1").fetchone()[0])
    finally:
        conexao.close()


def cadastrar_usuario(nome: str, email: str, senha_hash: str, perfil: str = "estudante") -> int:
    """Cadastra usuário; verifica duplicidade e grava na mesma transação."""
    nome = _validar_nome(nome)
    email = normalizar_email(email)
    _validar_hash(senha_hash)
    if perfil not in PERFIS_PERMITIDOS:
        raise ValueError("Perfil de usuário inválido.")
    conexao = conectar_banco()
    try:
        conexao.execute("BEGIN IMMEDIATE")
        if _email_em_uso(conexao.cursor(), email):
            raise ValueError("Já existe um usuário cadastrado com este e-mail.")
        cursor = conexao.execute(
            "INSERT INTO usuarios (nome, email, senha_hash, perfil, ativo) VALUES (?, ?, ?, ?, 1)",
            (nome, email, senha_hash, perfil)
        )
        usuario_id = int(cursor.lastrowid)
        conexao.commit()
        return usuario_id
    except sqlite3.IntegrityError as erro:
        conexao.rollback()
        raise ValueError("Não foi possível cadastrar o usuário. Verifique se o e-mail já está cadastrado.") from erro
    except (ValueError, sqlite3.Error):
        conexao.rollback()
        raise
    finally:
        conexao.close()


def cadastrar_primeiro_administrador(nome: str, email: str, senha_hash: str) -> int:
    """Impede dois bootstraps concorrentes e bloqueia um segundo administrador inicial."""
    nome = _validar_nome(nome)
    email = normalizar_email(email)
    _validar_hash(senha_hash)
    conexao = conectar_banco()
    try:
        conexao.execute("BEGIN IMMEDIATE")
        if conexao.execute("SELECT 1 FROM usuarios WHERE perfil = 'administrador' LIMIT 1").fetchone():
            raise AdministradorJaExisteError("Já existe um administrador cadastrado. O bootstrap está desabilitado.")
        if _email_em_uso(conexao.cursor(), email):
            raise ValueError("Já existe um usuário cadastrado com este e-mail.")
        cursor = conexao.execute(
            "INSERT INTO usuarios (nome, email, senha_hash, perfil, ativo) VALUES (?, ?, ?, 'administrador', 1)",
            (nome, email, senha_hash)
        )
        usuario_id = int(cursor.lastrowid)
        conexao.commit()
        return usuario_id
    except sqlite3.IntegrityError as erro:
        conexao.rollback()
        raise ValueError("Não foi possível cadastrar o primeiro administrador.") from erro
    except (AdministradorJaExisteError, ValueError, sqlite3.Error):
        conexao.rollback()
        raise
    finally:
        conexao.close()


def buscar_usuario(usuario_id: int) -> Usuario | None:
    """Busca um usuário pelo identificador."""
    _validar_usuario_id(usuario_id)
    conexao = conectar_banco()
    try:
        registro = conexao.execute("SELECT * FROM usuarios WHERE id = ?", (usuario_id,)).fetchone()
        return _registro_para_usuario(registro) if registro else None
    finally:
        conexao.close()


def buscar_usuario_por_email(email: str) -> Usuario | None:
    """Localiza um cadastro pelo e-mail normalizado."""
    email = normalizar_email(email)
    conexao = conectar_banco()
    try:
        registro = conexao.execute("SELECT * FROM usuarios WHERE LOWER(email) = ?", (email,)).fetchone()
        return _registro_para_usuario(registro) if registro else None
    finally:
        conexao.close()


def listar_usuarios(somente_ativos: bool = False) -> list[Usuario]:
    """Lista usuários para as operações administrativas autorizadas pela rota."""
    conexao = conectar_banco()
    try:
        sql = "SELECT * FROM usuarios"
        if somente_ativos:
            sql += " WHERE ativo = 1"
        sql += " ORDER BY nome, id"
        return [_registro_para_usuario(registro) for registro in conexao.execute(sql)]
    finally:
        conexao.close()


def atualizar_usuario(usuario_id: int, nome: str, email: str) -> bool:
    """Atualiza apenas nome e e-mail de usuário ativo, com verificação atômica."""
    _validar_usuario_id(usuario_id)
    nome = _validar_nome(nome)
    email = normalizar_email(email)
    conexao = conectar_banco()
    try:
        conexao.execute("BEGIN IMMEDIATE")
        registro = conexao.execute("SELECT ativo FROM usuarios WHERE id = ?", (usuario_id,)).fetchone()
        if registro is None:
            raise ValueError("Usuário não encontrado.")
        if not registro["ativo"]:
            raise ValueError("Usuário inativo não pode alterar o cadastro.")
        if _email_em_uso(conexao.cursor(), email, usuario_id):
            raise ValueError("Já existe outro usuário cadastrado com este e-mail.")
        cursor = conexao.execute(
            "UPDATE usuarios SET nome = ?, email = ? WHERE id = ? AND ativo = 1", (nome, email, usuario_id)
        )
        conexao.commit()
        return cursor.rowcount > 0
    except sqlite3.IntegrityError as erro:
        conexao.rollback()
        raise ValueError("O e-mail informado já está cadastrado.") from erro
    except (ValueError, sqlite3.Error):
        conexao.rollback()
        raise
    finally:
        conexao.close()


def atualizar_senha_hash(usuario_id: int, senha_hash: str, hash_anterior: str | None = None) -> bool:
    """Atualiza a senha de usuário ativo e admite comparação com o hash anterior."""
    _validar_usuario_id(usuario_id)
    _validar_hash(senha_hash)
    conexao = conectar_banco()
    try:
        if hash_anterior is None:
            cursor = conexao.execute(
                "UPDATE usuarios SET senha_hash = ? WHERE id = ? AND ativo = 1", (senha_hash, usuario_id)
            )
        else:
            cursor = conexao.execute(
                "UPDATE usuarios SET senha_hash = ? WHERE id = ? AND ativo = 1 AND senha_hash = ?",
                (senha_hash, usuario_id, hash_anterior)
            )
        conexao.commit()
        return cursor.rowcount > 0
    except sqlite3.Error:
        conexao.rollback()
        raise
    finally:
        conexao.close()


def alterar_perfil(usuario_id: int, perfil: str) -> bool:
    """Altera perfil sem permitir a perda do último administrador ativo."""
    _validar_usuario_id(usuario_id)
    if perfil not in PERFIS_PERMITIDOS:
        raise ValueError("Perfil de usuário inválido.")
    conexao = conectar_banco()
    try:
        conexao.execute("BEGIN IMMEDIATE")
        usuario = conexao.execute("SELECT perfil, ativo FROM usuarios WHERE id = ?", (usuario_id,)).fetchone()
        if usuario is None:
            conexao.rollback()
            return False
        if usuario["perfil"] == "administrador" and usuario["ativo"] and perfil != "administrador":
            quantidade = conexao.execute(
                "SELECT COUNT(*) FROM usuarios WHERE perfil = 'administrador' AND ativo = 1"
            ).fetchone()[0]
            if quantidade <= 1:
                raise ValueError("O último administrador ativo não pode perder o perfil de administrador.")
        conexao.execute("UPDATE usuarios SET perfil = ? WHERE id = ?", (perfil, usuario_id))
        conexao.commit()
        return True
    except (ValueError, sqlite3.Error):
        conexao.rollback()
        raise
    finally:
        conexao.close()


def ativar_usuario(usuario_id: int) -> bool:
    """Reativa um usuário cadastrado, sem criar registros adicionais."""
    _validar_usuario_id(usuario_id)
    conexao = conectar_banco()
    try:
        cursor = conexao.execute("UPDATE usuarios SET ativo = 1 WHERE id = ?", (usuario_id,))
        conexao.commit()
        return cursor.rowcount > 0
    except sqlite3.Error:
        conexao.rollback()
        raise
    finally:
        conexao.close()


def inativar_usuario(usuario_id: int) -> bool:
    """Inativa o usuário, respeitando a presença de outro administrador ativo."""
    _validar_usuario_id(usuario_id)
    conexao = conectar_banco()
    try:
        conexao.execute("BEGIN IMMEDIATE")
        usuario = conexao.execute("SELECT perfil, ativo FROM usuarios WHERE id = ?", (usuario_id,)).fetchone()
        if usuario is None:
            conexao.rollback()
            return False
        if not usuario["ativo"]:
            conexao.commit()
            return True
        if usuario["perfil"] == "administrador":
            quantidade = conexao.execute(
                "SELECT COUNT(*) FROM usuarios WHERE perfil = 'administrador' AND ativo = 1"
            ).fetchone()[0]
            if quantidade <= 1:
                raise ValueError("O último administrador ativo não pode ser inativado.")
        conexao.execute("UPDATE usuarios SET ativo = 0 WHERE id = ?", (usuario_id,))
        conexao.commit()
        return True
    except (ValueError, sqlite3.Error):
        conexao.rollback()
        raise
    finally:
        conexao.close()


def registrar_ultimo_acesso(usuario_id: int) -> None:
    """Registra o último acesso em UTC, sem alterar credenciais ou perfil."""
    _validar_usuario_id(usuario_id)
    data = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    conexao = conectar_banco()
    try:
        conexao.execute("UPDATE usuarios SET ultimo_acesso = ? WHERE id = ?", (data, usuario_id))
        conexao.commit()
    except sqlite3.Error:
        conexao.rollback()
        raise
    finally:
        conexao.close()


def _registro_para_usuario(registro: sqlite3.Row) -> Usuario:
    """Converte uma linha SQLite em um objeto Usuario, sem omitir dados internos necessários."""
    return Usuario(
        id=registro["id"], nome=registro["nome"], email=registro["email"],
        senha_hash=registro["senha_hash"], perfil=registro["perfil"],
        ativo=bool(registro["ativo"]), data_criacao=registro["data_criacao"],
        ultimo_acesso=registro["ultimo_acesso"]
    )
