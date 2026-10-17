"""Funções responsáveis pela autenticação e proteção das credenciais."""

import hmac
import os

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

try:
    from .models import Usuario
    from .usuarios import (
        AdministradorJaExisteError,
        atualizar_senha_hash,
        buscar_usuario,
        buscar_usuario_por_email,
        cadastrar_primeiro_administrador as cadastrar_primeiro_administrador_banco,
        cadastrar_usuario,
        registrar_ultimo_acesso
    )
except ImportError:
    from models import Usuario
    from usuarios import (
        AdministradorJaExisteError,
        atualizar_senha_hash,
        buscar_usuario,
        buscar_usuario_por_email,
        cadastrar_primeiro_administrador as cadastrar_primeiro_administrador_banco,
        cadastrar_usuario,
        registrar_ultimo_acesso
    )

# Objeto usado para criar e conferir hashes de senha com Argon2.
password_hasher = PasswordHasher()

# Nome da variável de ambiente e tamanho mínimo do token usado no primeiro administrador.
NOME_VARIAVEL_BOOTSTRAP = "ADMIN_BOOTSTRAP_TOKEN"
TAMANHO_MINIMO_TOKEN_BOOTSTRAP = 32


def validar_senha(senha: str) -> None:
    """Confere se a senha possui pelo menos 8 caracteres, uma letra e um número."""
    # Primeiro verifica se a senha foi informada no formato esperado.
    if senha is None:
        raise ValueError("A senha é obrigatória.")

    if not isinstance(senha, str):
        raise ValueError("A senha deve ser um texto.")

    if len(senha) < 8:
        raise ValueError("A senha deve possuir pelo menos 8 caracteres.")

    # Percorre os caracteres para verificar se existe pelo menos uma letra e um número.
    possui_letra = any(caractere.isalpha() for caractere in senha)
    possui_numero = any(caractere.isdigit() for caractere in senha)

    if not possui_letra:
        raise ValueError("A senha deve possuir pelo menos uma letra.")

    if not possui_numero:
        raise ValueError("A senha deve possuir pelo menos um número.")


def gerar_hash_senha(senha: str) -> str:
    """Valida a senha e devolve o hash Argon2 que será salvo no banco."""
    validar_senha(senha)
    return password_hasher.hash(senha)


def verificar_senha(senha: str, senha_hash: str) -> bool:
    """Confere se uma senha em texto corresponde ao hash salvo no banco."""
    if not senha or not senha_hash:
        return False

    try:
        return password_hasher.verify(senha_hash, senha)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        # Qualquer falha de verificação é tratada como senha incorreta.
        return False


def cadastrar_estudante(nome: str, email: str, senha: str) -> int:
    """Cria um usuário estudante e impede que o cadastro público escolha outro perfil."""
    # A senha é transformada em hash antes de ser enviada para a camada de usuários.
    senha_hash = gerar_hash_senha(senha)

    return cadastrar_usuario(
        nome=nome,
        email=email,
        senha_hash=senha_hash,
        perfil="estudante"
    )


def _obter_token_bootstrap_admin() -> str:
    """Lê e valida o token configurado para a criação do primeiro administrador."""
    # O token precisa vir da variável de ambiente e não possui valor padrão no código.
    token = os.getenv(NOME_VARIAVEL_BOOTSTRAP)

    if not token:
        raise RuntimeError("A variável ADMIN_BOOTSTRAP_TOKEN não foi configurada.")

    token = token.strip()

    if len(token) < TAMANHO_MINIMO_TOKEN_BOOTSTRAP:
        raise RuntimeError(
            f"ADMIN_BOOTSTRAP_TOKEN deve possuir pelo menos {TAMANHO_MINIMO_TOKEN_BOOTSTRAP} caracteres."
        )

    return token


def validar_token_bootstrap_admin(token_recebido: str | None) -> bool:
    """Compara o token recebido no cadastro do primeiro administrador com o token configurado."""
    token_esperado = _obter_token_bootstrap_admin()

    if not token_recebido:
        return False

    # compare_digest faz a comparação de forma mais adequada para valores sensíveis.
    return hmac.compare_digest(token_esperado, token_recebido)


def cadastrar_primeiro_administrador(
    nome: str,
    email: str,
    senha: str,
    token_bootstrap: str | None
) -> int:
    """Cria o primeiro administrador quando o token de bootstrap está correto."""
    # O token é validado antes de gerar o hash e tentar gravar o administrador.
    if not validar_token_bootstrap_admin(token_bootstrap):
        raise PermissionError("Token de bootstrap inválido.")

    senha_hash = gerar_hash_senha(senha)

    return cadastrar_primeiro_administrador_banco(
        nome=nome,
        email=email,
        senha_hash=senha_hash
    )


def autenticar_usuario(email: str, senha: str) -> Usuario | None:
    """Valida e-mail e senha e devolve o usuário quando as credenciais estão corretas."""
    if not email or not senha:
        return None

    # Busca o cadastro pelo e-mail informado.
    usuario = buscar_usuario_por_email(email)

    if usuario is None:
        return None

    if not usuario.ativo:
        return None

    if not verificar_senha(senha, usuario.senha_hash):
        return None

    # Atualiza o hash quando o Argon2 indicar que os parâmetros de segurança mudaram.
    atualizar_hash_se_necessario(usuario, senha)

    # Registra o login e busca novamente o usuário para devolver os dados atualizados.
    registrar_ultimo_acesso(usuario.id)
    return buscar_usuario(usuario.id)


def alterar_senha(usuario_id: int, senha_atual: str, nova_senha: str) -> bool:
    """Altera a senha do próprio usuário depois de conferir a senha atual."""
    usuario = buscar_usuario(usuario_id)

    if usuario is None:
        raise ValueError("Usuário não encontrado.")

    if not usuario.ativo:
        raise ValueError("O usuário está inativo.")

    # A senha atual precisa estar correta antes de permitir a troca.
    if not verificar_senha(senha_atual, usuario.senha_hash):
        raise ValueError("A senha atual está incorreta.")

    # Evita que a nova senha seja igual à senha já usada.
    if verificar_senha(nova_senha, usuario.senha_hash):
        raise ValueError("A nova senha deve ser diferente da senha atual.")

    novo_hash = gerar_hash_senha(nova_senha)
    return atualizar_senha_hash(usuario_id, novo_hash)


def atualizar_hash_se_necessario(usuario: Usuario, senha: str) -> None:
    """Gera um novo hash quando os parâmetros atuais do Argon2 ficarem diferentes do hash salvo."""
    try:
        precisa_atualizar = password_hasher.check_needs_rehash(usuario.senha_hash)
    except InvalidHashError:
        # Um hash inválido já é tratado como falha de autenticação em verificar_senha.
        return

    if not precisa_atualizar:
        return

    novo_hash = password_hasher.hash(senha)
    atualizar_senha_hash(usuario.id, novo_hash)


def possui_perfil(usuario: Usuario, perfil: str) -> bool:
    """Verifica se o usuário está ativo e possui o perfil informado."""
    if usuario is None:
        return False

    if not usuario.ativo:
        return False

    return usuario.perfil == perfil


def eh_administrador(usuario: Usuario) -> bool:
    """Retorna True quando o usuário ativo possui perfil de administrador."""
    return possui_perfil(usuario, "administrador")


def eh_estudante(usuario: Usuario) -> bool:
    """Retorna True quando o usuário ativo possui perfil de estudante."""
    return possui_perfil(usuario, "estudante")


def exigir_administrador(usuario: Usuario) -> None:
    """Interrompe a operação quando o usuário não possui perfil de administrador."""
    if not eh_administrador(usuario):
        raise PermissionError("Esta operação exige perfil de administrador.")


def exigir_usuario_ativo(usuario: Usuario) -> None:
    """Interrompe a operação quando não existe usuário autenticado ou quando ele está inativo."""
    if usuario is None:
        raise PermissionError("Usuário não autenticado.")

    if not usuario.ativo:
        raise PermissionError("Usuário inativo.")