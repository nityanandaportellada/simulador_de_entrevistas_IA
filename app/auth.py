
"""Autenticação, hashes de senha e cadastro público seguro."""

import hmac
import os

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

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

password_hasher = PasswordHasher()
# Verificação fictícia evita que um e-mail inexistente seja identificado pelo tempo da resposta.
HASH_FICTICIO = password_hasher.hash("SenhaFicticiaNaoUtilizada123")
NOME_VARIAVEL_BOOTSTRAP = "ADMIN_BOOTSTRAP_TOKEN"
TAMANHO_MINIMO_TOKEN_BOOTSTRAP = 32


def validar_senha(senha: str) -> None:
    """Exige senha com 8 a 128 caracteres, uma letra e um número."""
    if not isinstance(senha, str) or not senha:
        raise ValueError("A senha é obrigatória.")
    if len(senha) < 8 or len(senha) > 128:
        raise ValueError("A senha deve possuir entre 8 e 128 caracteres.")
    if not any(caractere.isalpha() for caractere in senha):
        raise ValueError("A senha deve possuir pelo menos uma letra.")
    if not any(caractere.isdigit() for caractere in senha):
        raise ValueError("A senha deve possuir pelo menos um número.")


def gerar_hash_senha(senha: str) -> str:
    """Valida a senha e gera um hash Argon2 para o SQLite."""
    validar_senha(senha)
    return password_hasher.hash(senha)


def verificar_senha(senha: str, senha_hash: str) -> bool:
    """Compara a senha com o hash, sem expor o motivo de falha."""
    if not isinstance(senha, str) or not senha or not senha_hash:
        return False
    try:
        return password_hasher.verify(senha_hash, senha)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def cadastrar_estudante(nome: str, email: str, senha: str) -> int:
    """Cadastra somente estudante, sem aceitar perfil administrativo na rota pública."""
    senha_hash = gerar_hash_senha(senha)
    return cadastrar_usuario(nome=nome, email=email, senha_hash=senha_hash, perfil="estudante")


def _obter_token_bootstrap_admin() -> str:
    """Exige token administrativo configurado no ambiente, sem valor padrão."""
    token = os.getenv(NOME_VARIAVEL_BOOTSTRAP, "").strip()
    if len(token) < TAMANHO_MINIMO_TOKEN_BOOTSTRAP:
        raise RuntimeError("Configure ADMIN_BOOTSTRAP_TOKEN com pelo menos 32 caracteres.")
    return token


def validar_token_bootstrap_admin(token_recebido: str | None) -> bool:
    """Compara o token recebido usando comparação resistente a variações de tempo."""
    esperado = _obter_token_bootstrap_admin()
    return bool(token_recebido) and hmac.compare_digest(esperado, token_recebido)


def cadastrar_primeiro_administrador(nome: str, email: str, senha: str, token_bootstrap: str | None) -> int:
    """Exige token correto e impede bootstrap repetido pela transação do serviço."""
    if not validar_token_bootstrap_admin(token_bootstrap):
        raise PermissionError("Token de bootstrap inválido.")
    senha_hash = gerar_hash_senha(senha)
    return cadastrar_primeiro_administrador_banco(nome=nome, email=email, senha_hash=senha_hash)


def autenticar_usuario(email: str, senha: str) -> Usuario | None:
    """Valida credenciais e reduz a diferença de tempo entre usuários existentes e ausentes."""
    if not isinstance(email, str) or not isinstance(senha, str) or not email or not senha:
        return None
    usuario = buscar_usuario_por_email(email)
    if usuario is None or not usuario.ativo:
        verificar_senha(senha, HASH_FICTICIO)
        return None
    if not verificar_senha(senha, usuario.senha_hash):
        return None
    atualizar_hash_se_necessario(usuario, senha)
    registrar_ultimo_acesso(usuario.id)
    return buscar_usuario(usuario.id)


def alterar_senha(usuario_id: int, senha_atual: str, nova_senha: str) -> bool:
    """Altera a senha do usuário após validar a atual e a nova."""
    usuario = buscar_usuario(usuario_id)
    if usuario is None:
        raise ValueError("Usuário não encontrado.")
    if not usuario.ativo:
        raise ValueError("O usuário está inativo.")
    if not verificar_senha(senha_atual, usuario.senha_hash):
        raise ValueError("A senha atual está incorreta.")
    validar_senha(nova_senha)
    if verificar_senha(nova_senha, usuario.senha_hash):
        raise ValueError("A nova senha deve ser diferente da senha atual.")
    return atualizar_senha_hash(usuario_id, gerar_hash_senha(nova_senha))


def atualizar_hash_se_necessario(usuario: Usuario, senha: str) -> None:
    """Atualiza o hash Argon2 quando os parâmetros recomendados mudam."""
    try:
        precisa_atualizar = password_hasher.check_needs_rehash(usuario.senha_hash)
    except InvalidHashError:
        return
    if precisa_atualizar:
        atualizar_senha_hash(usuario.id, password_hasher.hash(senha))


def possui_perfil(usuario: Usuario | None, perfil: str) -> bool:
    """Confirma se o usuário existe, está ativo e tem o perfil esperado."""
    return usuario is not None and usuario.ativo and usuario.perfil == perfil


def eh_administrador(usuario: Usuario | None) -> bool:
    """Verifica o perfil administrador."""
    return possui_perfil(usuario, "administrador")


def eh_estudante(usuario: Usuario | None) -> bool:
    """Verifica o perfil estudante."""
    return possui_perfil(usuario, "estudante")


def exigir_administrador(usuario: Usuario | None) -> None:
    """Rejeita operações sem administrador ativo."""
    if not eh_administrador(usuario):
        raise PermissionError("Esta operação exige perfil de administrador.")


def exigir_usuario_ativo(usuario: Usuario | None) -> None:
    """Rejeita usuários não autenticados ou inativos."""
    if usuario is None:
        raise PermissionError("Usuário não autenticado.")
    if not usuario.ativo:
        raise PermissionError("Usuário inativo.")
