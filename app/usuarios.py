"""
usuarios.py

Módulo responsável pelo gerenciamento dos usuários
do Simulador de Entrevistas.

Versão: 0.3

Responsabilidades:

- cadastrar usuários;
- cadastrar o primeiro administrador;
- buscar usuários;
- listar usuários;
- atualizar dados cadastrais;
- alterar perfil;
- ativar usuários;
- inativar usuários;
- verificar existência de e-mail;
- verificar existência de administrador;
- contar administradores ativos;
- proteger o último administrador ativo;
- registrar último acesso.

IMPORTANTE:

Este módulo NÃO recebe nem armazena senhas em texto puro.

O hash da senha deve ser produzido pelo módulo auth.py
antes do cadastro ou da alteração da senha.

REGRAS ADMINISTRATIVAS:

- deve existir pelo menos um administrador ativo;
- o último administrador ativo não pode perder
  o perfil de administrador;
- o último administrador ativo não pode ser inativado;
- a verificação ocorre dentro de transação para evitar
  problemas de concorrência.
"""

import sqlite3

from datetime import datetime


try:

    from .database import conectar_banco

    from .models import Usuario


except ImportError:

    from database import conectar_banco

    from models import Usuario


# ============================================================
# PERFIS PERMITIDOS
# ============================================================

PERFIS_PERMITIDOS = (
    "estudante",
    "administrador"
)


# ============================================================
# EXCEÇÕES ESPECÍFICAS
# ============================================================

class AdministradorJaExisteError(
    ValueError
):
    """
    Indica que o bootstrap administrativo
    não pode mais ser executado porque
    já existe administrador cadastrado.
    """

    pass


# ============================================================
# NORMALIZAR E-MAIL
# ============================================================

def normalizar_email(
    email: str
) -> str:
    """
    Remove espaços e converte o e-mail
    para letras minúsculas.
    """

    if email is None:

        raise ValueError(
            "O e-mail é obrigatório."
        )


    if not isinstance(
        email,
        str
    ):

        raise ValueError(
            "O e-mail deve ser um texto."
        )


    email = email.strip().lower()


    if not email:

        raise ValueError(
            "O e-mail é obrigatório."
        )


    return email


# ============================================================
# VALIDAR NOME
# ============================================================

def _validar_nome(
    nome: str
) -> str:
    """
    Valida e normaliza o nome do usuário.
    """

    if nome is None:

        raise ValueError(
            "O nome é obrigatório."
        )


    if not isinstance(
        nome,
        str
    ):

        raise ValueError(
            "O nome deve ser um texto."
        )


    nome = nome.strip()


    if not nome:

        raise ValueError(
            "O nome é obrigatório."
        )


    return nome


# ============================================================
# VALIDAR ID
# ============================================================

def _validar_usuario_id(
    usuario_id: int
) -> None:
    """
    Valida o ID de um usuário.
    """

    if not isinstance(
        usuario_id,
        int
    ):

        raise ValueError(
            "O ID do usuário deve ser um número inteiro."
        )


    if usuario_id <= 0:

        raise ValueError(
            "O ID do usuário é inválido."
        )


# ============================================================
# VERIFICAR E-MAIL
# ============================================================

def email_existe(
    email: str,
    ignorar_usuario_id: int | None = None
) -> bool:
    """
    Verifica se determinado e-mail já está
    cadastrado no sistema.

    O parâmetro ignorar_usuario_id é utilizado
    durante alterações cadastrais.
    """

    email = normalizar_email(
        email
    )


    conexao = conectar_banco()

    cursor = conexao.cursor()


    try:

        if ignorar_usuario_id is None:

            cursor.execute(
                """
                SELECT 1

                FROM usuarios

                WHERE LOWER(email) = LOWER(?)

                LIMIT 1
                """,
                (
                    email,
                )
            )


        else:

            _validar_usuario_id(
                ignorar_usuario_id
            )


            cursor.execute(
                """
                SELECT 1

                FROM usuarios

                WHERE LOWER(email) = LOWER(?)

                  AND id <> ?

                LIMIT 1
                """,
                (
                    email,
                    ignorar_usuario_id
                )
            )


        return (
            cursor.fetchone()
            is not None
        )


    finally:

        conexao.close()


# ============================================================
# VERIFICAR SE EXISTE ADMINISTRADOR
# ============================================================

def administrador_existe() -> bool:
    """
    Verifica se existe pelo menos um usuário
    com perfil de administrador.

    Considera administradores ativos ou inativos.

    Um administrador inativo não deve fazer
    o sistema retornar ao estado de bootstrap.
    """

    conexao = conectar_banco()

    cursor = conexao.cursor()


    try:

        cursor.execute(
            """
            SELECT 1

            FROM usuarios

            WHERE perfil = 'administrador'

            LIMIT 1
            """
        )


        return (
            cursor.fetchone()
            is not None
        )


    finally:

        conexao.close()


# ============================================================
# CONTAR ADMINISTRADORES ATIVOS
# ============================================================

def contar_administradores_ativos() -> int:
    """
    Retorna a quantidade de administradores ativos.

    Esta função é útil para auditoria,
    testes e validações administrativas.
    """

    conexao = conectar_banco()

    cursor = conexao.cursor()


    try:

        cursor.execute(
            """
            SELECT COUNT(*) AS quantidade

            FROM usuarios

            WHERE perfil = 'administrador'

              AND ativo = 1
            """
        )


        registro = cursor.fetchone()


        return int(
            registro["quantidade"]
        )


    finally:

        conexao.close()


# ============================================================
# CADASTRAR USUÁRIO
# ============================================================

def cadastrar_usuario(
    nome: str,
    email: str,
    senha_hash: str,
    perfil: str = "estudante"
) -> int:
    """
    Cadastra um novo usuário.

    A senha recebida por esta função deve estar
    previamente protegida por hash.

    Retorna o ID do usuário criado.
    """

    nome = _validar_nome(
        nome
    )


    email = normalizar_email(
        email
    )


    if not senha_hash:

        raise ValueError(
            "O hash da senha é obrigatório."
        )


    if perfil not in PERFIS_PERMITIDOS:

        raise ValueError(
            "Perfil de usuário inválido."
        )


    if email_existe(
        email
    ):

        raise ValueError(
            "Já existe um usuário cadastrado "
            "com este e-mail."
        )


    conexao = conectar_banco()

    cursor = conexao.cursor()


    try:

        cursor.execute(
            """
            INSERT INTO usuarios (
                nome,
                email,
                senha_hash,
                perfil,
                ativo
            )

            VALUES (?, ?, ?, ?, 1)
            """,
            (
                nome,
                email,
                senha_hash,
                perfil
            )
        )


        usuario_id = (
            cursor.lastrowid
        )


        conexao.commit()


        return usuario_id


    except sqlite3.IntegrityError as erro:

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


# ============================================================
# CADASTRAR PRIMEIRO ADMINISTRADOR
# ============================================================

def cadastrar_primeiro_administrador(
    nome: str,
    email: str,
    senha_hash: str
) -> int:
    """
    Cadastra o primeiro administrador do sistema.

    Esta função somente funciona enquanto não existir
    nenhum administrador cadastrado.

    A validação e a inserção são realizadas dentro
    da mesma transação.

    BEGIN IMMEDIATE impede que duas requisições
    concorrentes criem simultaneamente dois
    administradores durante o bootstrap.
    """

    nome = _validar_nome(
        nome
    )


    email = normalizar_email(
        email
    )


    if not senha_hash:

        raise ValueError(
            "O hash da senha é obrigatório."
        )


    conexao = conectar_banco()

    cursor = conexao.cursor()


    try:

        # --------------------------------------------------------
        # BLOQUEAR TRANSAÇÃO PARA ESCRITA
        # --------------------------------------------------------

        cursor.execute(
            "BEGIN IMMEDIATE"
        )


        # --------------------------------------------------------
        # VERIFICAR ADMINISTRADOR EXISTENTE
        # --------------------------------------------------------

        cursor.execute(
            """
            SELECT 1

            FROM usuarios

            WHERE perfil = 'administrador'

            LIMIT 1
            """
        )


        if (
            cursor.fetchone()
            is not None
        ):

            raise AdministradorJaExisteError(
                "Já existe um administrador cadastrado. "
                "O bootstrap administrativo está desabilitado."
            )


        # --------------------------------------------------------
        # VERIFICAR E-MAIL
        # --------------------------------------------------------

        cursor.execute(
            """
            SELECT 1

            FROM usuarios

            WHERE LOWER(email) = LOWER(?)

            LIMIT 1
            """,
            (
                email,
            )
        )


        if (
            cursor.fetchone()
            is not None
        ):

            raise ValueError(
                "Já existe um usuário cadastrado "
                "com este e-mail."
            )


        # --------------------------------------------------------
        # CRIAR ADMINISTRADOR
        # --------------------------------------------------------

        cursor.execute(
            """
            INSERT INTO usuarios (
                nome,
                email,
                senha_hash,
                perfil,
                ativo
            )

            VALUES (?, ?, ?, 'administrador', 1)
            """,
            (
                nome,
                email,
                senha_hash
            )
        )


        usuario_id = (
            cursor.lastrowid
        )


        conexao.commit()


        return usuario_id


    except (
        AdministradorJaExisteError,
        ValueError
    ):

        conexao.rollback()

        raise


    except sqlite3.IntegrityError as erro:

        conexao.rollback()


        raise ValueError(
            "Não foi possível cadastrar "
            "o primeiro administrador."
        ) from erro


    except sqlite3.Error:

        conexao.rollback()

        raise


    finally:

        conexao.close()


# ============================================================
# BUSCAR USUÁRIO
# ============================================================

def buscar_usuario(
    usuario_id: int
) -> Usuario | None:
    """
    Busca um usuário pelo ID.
    """

    _validar_usuario_id(
        usuario_id
    )


    conexao = conectar_banco()

    cursor = conexao.cursor()


    try:

        cursor.execute(
            """
            SELECT *

            FROM usuarios

            WHERE id = ?
            """,
            (
                usuario_id,
            )
        )


        registro = cursor.fetchone()


        if registro is None:

            return None


        return _registro_para_usuario(
            registro
        )


    finally:

        conexao.close()


# ============================================================
# BUSCAR USUÁRIO PELO E-MAIL
# ============================================================

def buscar_usuario_por_email(
    email: str
) -> Usuario | None:
    """
    Busca um usuário pelo endereço de e-mail.
    """

    email = normalizar_email(
        email
    )


    conexao = conectar_banco()

    cursor = conexao.cursor()


    try:

        cursor.execute(
            """
            SELECT *

            FROM usuarios

            WHERE LOWER(email) = LOWER(?)
            """,
            (
                email,
            )
        )


        registro = cursor.fetchone()


        if registro is None:

            return None


        return _registro_para_usuario(
            registro
        )


    finally:

        conexao.close()


# ============================================================
# LISTAR USUÁRIOS
# ============================================================

def listar_usuarios(
    somente_ativos: bool = False
) -> list[Usuario]:
    """
    Lista os usuários cadastrados.

    Quando somente_ativos for True,
    retorna apenas usuários ativos.
    """

    conexao = conectar_banco()

    cursor = conexao.cursor()


    try:

        if somente_ativos:

            cursor.execute(
                """
                SELECT *

                FROM usuarios

                WHERE ativo = 1

                ORDER BY nome, id
                """
            )


        else:

            cursor.execute(
                """
                SELECT *

                FROM usuarios

                ORDER BY nome, id
                """
            )


        registros = cursor.fetchall()


        return [

            _registro_para_usuario(
                registro
            )

            for registro in registros

        ]


    finally:

        conexao.close()


# ============================================================
# ATUALIZAR DADOS
# ============================================================

def atualizar_usuario(
    usuario_id: int,
    nome: str,
    email: str
) -> bool:
    """
    Atualiza nome e e-mail de um usuário.

    Perfil, senha e status possuem funções
    específicas.
    """

    _validar_usuario_id(
        usuario_id
    )


    nome = _validar_nome(
        nome
    )


    email = normalizar_email(
        email
    )


    usuario = buscar_usuario(
        usuario_id
    )


    if usuario is None:

        raise ValueError(
            "Usuário não encontrado."
        )


    if email_existe(
        email,
        ignorar_usuario_id=usuario_id
    ):

        raise ValueError(
            "Já existe outro usuário cadastrado "
            "com este e-mail."
        )


    conexao = conectar_banco()

    cursor = conexao.cursor()


    try:

        cursor.execute(
            """
            UPDATE usuarios

            SET
                nome = ?,
                email = ?

            WHERE id = ?
            """,
            (
                nome,
                email,
                usuario_id
            )
        )


        conexao.commit()


        return (
            cursor.rowcount > 0
        )


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


# ============================================================
# ALTERAR SENHA HASH
# ============================================================

def atualizar_senha_hash(
    usuario_id: int,
    senha_hash: str
) -> bool:
    """
    Atualiza o hash da senha.

    Esta função não deve receber senha em texto puro.
    """

    _validar_usuario_id(
        usuario_id
    )


    if not senha_hash:

        raise ValueError(
            "O hash da senha é obrigatório."
        )


    conexao = conectar_banco()

    cursor = conexao.cursor()


    try:

        cursor.execute(
            """
            UPDATE usuarios

            SET senha_hash = ?

            WHERE id = ?
            """,
            (
                senha_hash,
                usuario_id
            )
        )


        conexao.commit()


        return (
            cursor.rowcount > 0
        )


    except sqlite3.Error:

        conexao.rollback()

        raise


    finally:

        conexao.close()


# ============================================================
# ALTERAR PERFIL
# ============================================================

def alterar_perfil(
    usuario_id: int,
    perfil: str
) -> bool:
    """
    Altera o perfil de um usuário.

    REGRA DE INTEGRIDADE:

    Se o usuário for o último administrador ativo,
    ele não poderá perder o perfil administrador.

    A verificação e a alteração são executadas
    dentro da mesma transação para evitar
    condições de corrida.
    """

    _validar_usuario_id(
        usuario_id
    )


    if perfil not in PERFIS_PERMITIDOS:

        raise ValueError(
            "Perfil de usuário inválido."
        )


    conexao = conectar_banco()

    cursor = conexao.cursor()


    try:

        # --------------------------------------------------------
        # BLOQUEAR ALTERAÇÕES CONCORRENTES
        # --------------------------------------------------------

        cursor.execute(
            "BEGIN IMMEDIATE"
        )


        # --------------------------------------------------------
        # BUSCAR USUÁRIO
        # --------------------------------------------------------

        cursor.execute(
            """
            SELECT
                id,
                perfil,
                ativo

            FROM usuarios

            WHERE id = ?
            """,
            (
                usuario_id,
            )
        )


        usuario = cursor.fetchone()


        if usuario is None:

            conexao.rollback()

            return False


        perfil_atual = (
            usuario["perfil"]
        )


        usuario_ativo = bool(
            usuario["ativo"]
        )


        # --------------------------------------------------------
        # PROTEGER ÚLTIMO ADMINISTRADOR ATIVO
        # --------------------------------------------------------

        if (
            perfil_atual == "administrador"
            and usuario_ativo
            and perfil != "administrador"
        ):

            cursor.execute(
                """
                SELECT COUNT(*) AS quantidade

                FROM usuarios

                WHERE perfil = 'administrador'

                  AND ativo = 1
                """
            )


            quantidade = int(
                cursor.fetchone()[
                    "quantidade"
                ]
            )


            if quantidade <= 1:

                raise ValueError(
                    "O último administrador ativo "
                    "não pode perder o perfil "
                    "de administrador."
                )


        # --------------------------------------------------------
        # ALTERAR PERFIL
        # --------------------------------------------------------

        cursor.execute(
            """
            UPDATE usuarios

            SET perfil = ?

            WHERE id = ?
            """,
            (
                perfil,
                usuario_id
            )
        )


        conexao.commit()


        return True


    except ValueError:

        conexao.rollback()

        raise


    except sqlite3.Error:

        conexao.rollback()

        raise


    finally:

        conexao.close()


# ============================================================
# ATIVAR USUÁRIO
# ============================================================

def ativar_usuario(
    usuario_id: int
) -> bool:
    """
    Ativa um usuário.
    """

    _validar_usuario_id(
        usuario_id
    )


    conexao = conectar_banco()

    cursor = conexao.cursor()


    try:

        cursor.execute(
            """
            SELECT id

            FROM usuarios

            WHERE id = ?
            """,
            (
                usuario_id,
            )
        )


        if cursor.fetchone() is None:

            return False


        cursor.execute(
            """
            UPDATE usuarios

            SET ativo = 1

            WHERE id = ?
            """,
            (
                usuario_id,
            )
        )


        conexao.commit()


        return True


    except sqlite3.Error:

        conexao.rollback()

        raise


    finally:

        conexao.close()


# ============================================================
# INATIVAR USUÁRIO
# ============================================================

def inativar_usuario(
    usuario_id: int
) -> bool:
    """
    Inativa um usuário.

    O usuário não é removido fisicamente do banco,
    preservando o histórico de entrevistas.

    REGRA DE INTEGRIDADE:

    O último administrador ativo não pode
    ser inativado.

    A verificação ocorre dentro da mesma
    transação da alteração.
    """

    _validar_usuario_id(
        usuario_id
    )


    conexao = conectar_banco()

    cursor = conexao.cursor()


    try:

        # --------------------------------------------------------
        # BLOQUEAR ALTERAÇÕES CONCORRENTES
        # --------------------------------------------------------

        cursor.execute(
            "BEGIN IMMEDIATE"
        )


        # --------------------------------------------------------
        # BUSCAR USUÁRIO
        # --------------------------------------------------------

        cursor.execute(
            """
            SELECT
                id,
                perfil,
                ativo

            FROM usuarios

            WHERE id = ?
            """,
            (
                usuario_id,
            )
        )


        usuario = cursor.fetchone()


        if usuario is None:

            conexao.rollback()

            return False


        usuario_ativo = bool(
            usuario["ativo"]
        )


        perfil = (
            usuario["perfil"]
        )


        # --------------------------------------------------------
        # USUÁRIO JÁ INATIVO
        # --------------------------------------------------------

        if not usuario_ativo:

            conexao.commit()

            return True


        # --------------------------------------------------------
        # PROTEGER ÚLTIMO ADMINISTRADOR
        # --------------------------------------------------------

        if perfil == "administrador":

            cursor.execute(
                """
                SELECT COUNT(*) AS quantidade

                FROM usuarios

                WHERE perfil = 'administrador'

                  AND ativo = 1
                """
            )


            quantidade = int(
                cursor.fetchone()[
                    "quantidade"
                ]
            )


            if quantidade <= 1:

                raise ValueError(
                    "O último administrador ativo "
                    "não pode ser inativado."
                )


        # --------------------------------------------------------
        # INATIVAR
        # --------------------------------------------------------

        cursor.execute(
            """
            UPDATE usuarios

            SET ativo = 0

            WHERE id = ?
            """,
            (
                usuario_id,
            )
        )


        conexao.commit()


        return True


    except ValueError:

        conexao.rollback()

        raise


    except sqlite3.Error:

        conexao.rollback()

        raise


    finally:

        conexao.close()


# ============================================================
# REGISTRAR ÚLTIMO ACESSO
# ============================================================

def registrar_ultimo_acesso(
    usuario_id: int
) -> None:
    """
    Registra a data e hora do último login
    realizado com sucesso.
    """

    _validar_usuario_id(
        usuario_id
    )


    data = datetime.now().isoformat(
        sep=" ",
        timespec="seconds"
    )


    conexao = conectar_banco()

    cursor = conexao.cursor()


    try:

        cursor.execute(
            """
            UPDATE usuarios

            SET ultimo_acesso = ?

            WHERE id = ?
            """,
            (
                data,
                usuario_id
            )
        )


        conexao.commit()


    except sqlite3.Error:

        conexao.rollback()

        raise


    finally:

        conexao.close()


# ============================================================
# CONVERTER REGISTRO
# ============================================================

def _registro_para_usuario(
    registro: sqlite3.Row
) -> Usuario:
    """
    Converte um registro SQLite
    em objeto Usuario.
    """

    return Usuario(

        id=registro[
            "id"
        ],

        nome=registro[
            "nome"
        ],

        email=registro[
            "email"
        ],

        senha_hash=registro[
            "senha_hash"
        ],

        perfil=registro[
            "perfil"
        ],

        ativo=bool(
            registro[
                "ativo"
            ]
        ),

        data_criacao=registro[
            "data_criacao"
        ],

        ultimo_acesso=registro[
            "ultimo_acesso"
        ]

    )