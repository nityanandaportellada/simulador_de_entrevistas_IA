"""
auth.py

Módulo responsável pela autenticação e proteção
das credenciais dos usuários.

Versão: 0.2

Responsabilidades:

- validar requisitos mínimos de senha;
- gerar hash seguro de senha;
- verificar senha;
- autenticar usuário;
- cadastrar estudante;
- cadastrar o primeiro administrador;
- validar token de bootstrap administrativo;
- alterar senha;
- verificar perfil;
- verificar autorização.

IMPORTANTE:

Senhas nunca são armazenadas em texto puro.

Este módulo utiliza Argon2 para proteção das senhas.

O primeiro administrador somente pode ser criado
mediante token de bootstrap configurado por
variável de ambiente.
"""

import hmac
import os


from argon2 import PasswordHasher


from argon2.exceptions import (
    VerifyMismatchError,
    VerificationError,
    InvalidHashError
)


try:

    from .models import Usuario


    from .usuarios import (
        AdministradorJaExisteError,
        cadastrar_usuario,
        cadastrar_primeiro_administrador as
        cadastrar_primeiro_administrador_banco,
        buscar_usuario,
        buscar_usuario_por_email,
        atualizar_senha_hash,
        registrar_ultimo_acesso
    )


except ImportError:

    from models import Usuario


    from usuarios import (
        AdministradorJaExisteError,
        cadastrar_usuario,
        cadastrar_primeiro_administrador as
        cadastrar_primeiro_administrador_banco,
        buscar_usuario,
        buscar_usuario_por_email,
        atualizar_senha_hash,
        registrar_ultimo_acesso
    )


# ============================================================
# CONFIGURAÇÃO DO HASH
# ============================================================

password_hasher = PasswordHasher()


# ============================================================
# CONFIGURAÇÃO DO BOOTSTRAP
# ============================================================

NOME_VARIAVEL_BOOTSTRAP = (
    "ADMIN_BOOTSTRAP_TOKEN"
)


TAMANHO_MINIMO_TOKEN_BOOTSTRAP = 32


# ============================================================
# VALIDAR SENHA
# ============================================================

def validar_senha(
    senha: str
) -> None:
    """
    Valida requisitos mínimos da senha.

    A política exige:

    - mínimo de 8 caracteres;
    - pelo menos uma letra;
    - pelo menos um número.
    """

    if senha is None:

        raise ValueError(
            "A senha é obrigatória."
        )


    if not isinstance(
        senha,
        str
    ):

        raise ValueError(
            "A senha deve ser um texto."
        )


    if len(senha) < 8:

        raise ValueError(
            "A senha deve possuir pelo menos "
            "8 caracteres."
        )


    possui_letra = any(
        caractere.isalpha()
        for caractere in senha
    )


    possui_numero = any(
        caractere.isdigit()
        for caractere in senha
    )


    if not possui_letra:

        raise ValueError(
            "A senha deve possuir pelo menos "
            "uma letra."
        )


    if not possui_numero:

        raise ValueError(
            "A senha deve possuir pelo menos "
            "um número."
        )


# ============================================================
# GERAR HASH
# ============================================================

def gerar_hash_senha(
    senha: str
) -> str:
    """
    Valida a senha e gera um hash Argon2.

    A senha original não é armazenada.
    """

    validar_senha(
        senha
    )


    return password_hasher.hash(
        senha
    )


# ============================================================
# VERIFICAR SENHA
# ============================================================

def verificar_senha(
    senha: str,
    senha_hash: str
) -> bool:
    """
    Verifica se uma senha corresponde
    ao hash armazenado.
    """

    if not senha or not senha_hash:

        return False


    try:

        return password_hasher.verify(
            senha_hash,
            senha
        )


    except (
        VerifyMismatchError,
        VerificationError,
        InvalidHashError
    ):

        return False


# ============================================================
# CADASTRAR ESTUDANTE
# ============================================================

def cadastrar_estudante(
    nome: str,
    email: str,
    senha: str
) -> int:
    """
    Cadastra um novo estudante.

    O usuário não pode escolher o perfil
    administrador por esta função.

    Isso impede elevação de privilégio
    durante um cadastro comum.
    """

    senha_hash = gerar_hash_senha(
        senha
    )


    return cadastrar_usuario(
        nome=nome,
        email=email,
        senha_hash=senha_hash,
        perfil="estudante"
    )


# ============================================================
# OBTER TOKEN DE BOOTSTRAP
# ============================================================

def _obter_token_bootstrap_admin() -> str:
    """
    Recupera o token administrativo de bootstrap.

    O token deve ser definido exclusivamente
    através da variável de ambiente:

        ADMIN_BOOTSTRAP_TOKEN

    Não existe valor padrão.
    """

    token = os.getenv(
        NOME_VARIAVEL_BOOTSTRAP
    )


    if not token:

        raise RuntimeError(
            "A variável ADMIN_BOOTSTRAP_TOKEN "
            "não foi configurada."
        )


    token = token.strip()


    if (
        len(token)
        < TAMANHO_MINIMO_TOKEN_BOOTSTRAP
    ):

        raise RuntimeError(
            "ADMIN_BOOTSTRAP_TOKEN deve possuir "
            f"pelo menos "
            f"{TAMANHO_MINIMO_TOKEN_BOOTSTRAP} "
            "caracteres."
        )


    return token


# ============================================================
# VALIDAR TOKEN DE BOOTSTRAP
# ============================================================

def validar_token_bootstrap_admin(
    token_recebido: str | None
) -> bool:
    """
    Compara o token recebido com o token
    configurado no ambiente.

    hmac.compare_digest é utilizado para evitar
    comparação simples de strings sensíveis.
    """

    token_esperado = (
        _obter_token_bootstrap_admin()
    )


    if not token_recebido:

        return False


    return hmac.compare_digest(
        token_esperado,
        token_recebido
    )


# ============================================================
# CADASTRAR PRIMEIRO ADMINISTRADOR
# ============================================================

def cadastrar_primeiro_administrador(
    nome: str,
    email: str,
    senha: str,
    token_bootstrap: str | None
) -> int:
    """
    Cadastra o primeiro administrador.

    Requisitos:

    - token de bootstrap correto;
    - senha válida;
    - inexistência de administrador anterior.

    Mesmo com o token correto, esta função deixa
    de funcionar permanentemente depois que
    o primeiro administrador é criado.
    """

    if not validar_token_bootstrap_admin(
        token_bootstrap
    ):

        raise PermissionError(
            "Token de bootstrap inválido."
        )


    senha_hash = gerar_hash_senha(
        senha
    )


    return (
        cadastrar_primeiro_administrador_banco(
            nome=nome,
            email=email,
            senha_hash=senha_hash
        )
    )


# ============================================================
# AUTENTICAR
# ============================================================

def autenticar_usuario(
    email: str,
    senha: str
) -> Usuario | None:
    """
    Autentica um usuário através
    de e-mail e senha.

    Retorna o objeto Usuario quando
    as credenciais estiverem corretas.

    Retorna None quando as credenciais
    forem inválidas.
    """

    if not email or not senha:

        return None


    usuario = buscar_usuario_por_email(
        email
    )


    if usuario is None:

        return None


    if not usuario.ativo:

        return None


    senha_correta = verificar_senha(
        senha,
        usuario.senha_hash
    )


    if not senha_correta:

        return None


    atualizar_hash_se_necessario(
        usuario,
        senha
    )


    registrar_ultimo_acesso(
        usuario.id
    )


    usuario = buscar_usuario(
        usuario.id
    )


    return usuario


# ============================================================
# ALTERAR SENHA
# ============================================================

def alterar_senha(
    usuario_id: int,
    senha_atual: str,
    nova_senha: str
) -> bool:
    """
    Permite que o próprio usuário altere
    sua senha.

    A senha atual deve ser informada corretamente.
    """

    usuario = buscar_usuario(
        usuario_id
    )


    if usuario is None:

        raise ValueError(
            "Usuário não encontrado."
        )


    if not usuario.ativo:

        raise ValueError(
            "O usuário está inativo."
        )


    if not verificar_senha(
        senha_atual,
        usuario.senha_hash
    ):

        raise ValueError(
            "A senha atual está incorreta."
        )


    # Impede reutilização imediata
    # da mesma senha.

    if verificar_senha(
        nova_senha,
        usuario.senha_hash
    ):

        raise ValueError(
            "A nova senha deve ser diferente "
            "da senha atual."
        )


    novo_hash = gerar_hash_senha(
        nova_senha
    )


    return atualizar_senha_hash(
        usuario_id,
        novo_hash
    )


# ============================================================
# REHASH DE SENHA
# ============================================================

def atualizar_hash_se_necessario(
    usuario: Usuario,
    senha: str
) -> None:
    """
    Atualiza o hash caso os parâmetros de segurança
    do Argon2 sejam modificados futuramente.

    Isso permite evolução gradual da proteção
    das senhas.
    """

    try:

        precisa_atualizar = (
            password_hasher.check_needs_rehash(
                usuario.senha_hash
            )
        )


    except InvalidHashError:

        return


    if not precisa_atualizar:

        return


    novo_hash = password_hasher.hash(
        senha
    )


    atualizar_senha_hash(
        usuario.id,
        novo_hash
    )


# ============================================================
# VERIFICAR PERFIL
# ============================================================

def possui_perfil(
    usuario: Usuario,
    perfil: str
) -> bool:
    """
    Verifica se o usuário possui determinado perfil.
    """

    if usuario is None:

        return False


    if not usuario.ativo:

        return False


    return (
        usuario.perfil
        == perfil
    )


# ============================================================
# VERIFICAR ADMINISTRADOR
# ============================================================

def eh_administrador(
    usuario: Usuario
) -> bool:
    """
    Verifica se o usuário possui
    perfil de administrador.
    """

    return possui_perfil(
        usuario,
        "administrador"
    )


# ============================================================
# VERIFICAR ESTUDANTE
# ============================================================

def eh_estudante(
    usuario: Usuario
) -> bool:
    """
    Verifica se o usuário possui
    perfil de estudante.
    """

    return possui_perfil(
        usuario,
        "estudante"
    )


# ============================================================
# EXIGIR ADMINISTRADOR
# ============================================================

def exigir_administrador(
    usuario: Usuario
) -> None:
    """
    Interrompe a operação caso o usuário
    não seja administrador.
    """

    if not eh_administrador(
        usuario
    ):

        raise PermissionError(
            "Esta operação exige perfil "
            "de administrador."
        )


# ============================================================
# EXIGIR USUÁRIO ATIVO
# ============================================================

def exigir_usuario_ativo(
    usuario: Usuario
) -> None:
    """
    Verifica se existe um usuário autenticado
    e se ele está ativo.
    """

    if usuario is None:

        raise PermissionError(
            "Usuário não autenticado."
        )


    if not usuario.ativo:

        raise PermissionError(
            "Usuário inativo."
        )