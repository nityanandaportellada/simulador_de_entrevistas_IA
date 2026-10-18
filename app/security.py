
"""Criação e validação de JWT e permissões de acesso à API."""

import hashlib
import hmac
import os
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .models import Usuario
from .usuarios import buscar_usuario

JWT_ALGORITHM = "HS256"
TOKEN_EXPIRACAO_MINUTOS = 60
TAMANHO_MINIMO_JWT_SECRET = 32
PERFIS_VALIDOS = ("estudante", "administrador")
bearer_scheme = HTTPBearer(auto_error=False)


def _nao_autorizado(mensagem: str = "Autenticação necessária.") -> HTTPException:
    """Padroniza o erro e informa que a API exige token Bearer."""
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=mensagem, headers={"WWW-Authenticate": "Bearer"})


def _obter_jwt_secret() -> str:
    """Exige uma chave de assinatura fornecida pelo ambiente."""
    segredo = os.getenv("JWT_SECRET", "")
    if len(segredo) < TAMANHO_MINIMO_JWT_SECRET or not segredo.strip():
        raise RuntimeError("Configure JWT_SECRET com pelo menos 32 caracteres aleatórios.")
    return segredo


def _versao_senha(senha_hash: str, segredo: str) -> str:
    """Gera um marcador assinado para invalidar tokens após troca de senha."""
    return hmac.new(segredo.encode("utf-8"), senha_hash.encode("utf-8"), hashlib.sha256).hexdigest()


def criar_token_acesso(usuario_id: int, perfil: str) -> str:
    """Emite JWT somente para usuário ativo e com perfil atual confirmado."""
    if not isinstance(usuario_id, int) or isinstance(usuario_id, bool) or usuario_id <= 0:
        raise ValueError("ID de usuário inválido.")
    if perfil not in PERFIS_VALIDOS:
        raise ValueError("Perfil de usuário inválido.")
    usuario = buscar_usuario(usuario_id)
    if usuario is None or not usuario.ativo or usuario.perfil != perfil:
        raise _nao_autorizado("Usuário ou permissões inválidas.")
    segredo = _obter_jwt_secret()
    agora = datetime.now(timezone.utc)
    payload = {
        "sub": str(usuario_id),
        "perfil": usuario.perfil,
        "pwdv": _versao_senha(usuario.senha_hash, segredo),
        "iat": agora,
        "exp": agora + timedelta(minutes=TOKEN_EXPIRACAO_MINUTOS)
    }
    return jwt.encode(payload, segredo, algorithm=JWT_ALGORITHM)


def decodificar_token(token: str) -> dict:
    """Confere assinatura, validade temporal, ID, perfil e marcador de senha."""
    if not isinstance(token, str) or not token:
        raise _nao_autorizado("Token inválido.")
    try:
        payload = jwt.decode(
            token, _obter_jwt_secret(), algorithms=[JWT_ALGORITHM],
            options={"require": ["sub", "perfil", "pwdv", "iat", "exp"]}
        )
    except jwt.ExpiredSignatureError as erro:
        raise _nao_autorizado("Token expirado.") from erro
    except jwt.InvalidTokenError as erro:
        raise _nao_autorizado("Token inválido.") from erro
    identificador = payload.get("sub")
    if not isinstance(identificador, str) or not identificador.isascii() or not identificador.isdecimal():
        raise _nao_autorizado("Token inválido.")
    if int(identificador) <= 0 or payload.get("perfil") not in PERFIS_VALIDOS:
        raise _nao_autorizado("Token inválido.")
    if not isinstance(payload.get("pwdv"), str) or len(payload["pwdv"]) != 64:
        raise _nao_autorizado("Token inválido.")
    for campo in ("iat", "exp"):
        if not isinstance(payload.get(campo), int) or isinstance(payload[campo], bool):
            raise _nao_autorizado("Token inválido.")
    if payload["exp"] <= payload["iat"] or payload["exp"] - payload["iat"] > TOKEN_EXPIRACAO_MINUTOS * 60:
        raise _nao_autorizado("Token inválido.")
    return payload


def obter_usuario_atual(credenciais: HTTPAuthorizationCredentials | None = Depends(bearer_scheme)) -> Usuario:
    """Confirma as permissões e a senha atuais antes de aceitar cada requisição."""
    if credenciais is None or credenciais.scheme.lower() != "bearer":
        raise _nao_autorizado()
    payload = decodificar_token(credenciais.credentials)
    usuario = buscar_usuario(int(payload["sub"]))
    if usuario is None:
        raise _nao_autorizado("Usuário não encontrado.")
    if not usuario.ativo:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Usuário inativo.")
    if usuario.perfil not in PERFIS_VALIDOS or usuario.perfil != payload["perfil"]:
        raise _nao_autorizado("Permissões alteradas. Entre novamente.")
    esperado = _versao_senha(usuario.senha_hash, _obter_jwt_secret())
    if not hmac.compare_digest(esperado, payload["pwdv"]):
        raise _nao_autorizado("Credenciais alteradas. Entre novamente.")
    return usuario


def obter_administrador_atual(usuario: Usuario = Depends(obter_usuario_atual)) -> Usuario:
    """Permite o acesso somente ao administrador ativo."""
    if usuario.perfil != "administrador":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Esta operação exige perfil de administrador.")
    return usuario
