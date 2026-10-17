"""Funções de segurança usadas pela API do Simulador de Entrevistas."""

import os
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

try:
    from .models import Usuario
    from .usuarios import buscar_usuario
except ImportError:
    from models import Usuario
    from usuarios import buscar_usuario

# Configurações usadas para criar e validar os tokens de acesso.
JWT_SECRET = os.getenv("JWT_SECRET")
JWT_ALGORITHM = "HS256"
TOKEN_EXPIRACAO_MINUTOS = 60

# Informa ao FastAPI que as rotas protegidas recebem um token Bearer.
bearer_scheme = HTTPBearer()


def _obter_jwt_secret() -> str:
    """Retorna a chave usada no JWT e impede o uso do sistema sem configuração."""
    # A chave deve vir da variável de ambiente e nunca ficar escrita no código.
    if not JWT_SECRET:
        raise RuntimeError("A variável JWT_SECRET não foi configurada.")

    return JWT_SECRET


def criar_token_acesso(usuario_id: int, perfil: str) -> str:
    """Cria um token JWT com o ID, o perfil e o tempo de validade do usuário."""
    # Registra o momento da criação e calcula quando o token deve expirar.
    agora = datetime.now(timezone.utc)
    expiracao = agora + timedelta(minutes=TOKEN_EXPIRACAO_MINUTOS)

    # O payload guarda somente os dados necessários para identificar o acesso.
    payload = {
        "sub": str(usuario_id),
        "perfil": perfil,
        "iat": agora,
        "exp": expiracao
    }

    # Assina o token usando a chave configurada no ambiente.
    return jwt.encode(payload, _obter_jwt_secret(), algorithm=JWT_ALGORITHM)


def decodificar_token(token: str) -> dict:
    """Valida o token recebido e devolve os dados que estavam guardados nele."""
    try:
        return jwt.decode(token, _obter_jwt_secret(), algorithms=[JWT_ALGORITHM])

    except jwt.ExpiredSignatureError:
        # Um token expirado não pode mais ser usado para acessar a API.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expirado."
        )

    except jwt.InvalidTokenError:
        # Qualquer outro problema de assinatura ou formato torna o token inválido.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido."
        )


def obter_usuario_atual(
    credenciais: HTTPAuthorizationCredentials = Depends(bearer_scheme)
) -> Usuario:
    """Identifica o usuário autenticado a partir do token enviado na requisição."""
    # Primeiro valida o token e recupera o campo sub, que contém o ID do usuário.
    payload = decodificar_token(credenciais.credentials)
    usuario_id = payload.get("sub")

    if usuario_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido."
        )

    # O ID fica gravado no token como texto e precisa voltar para inteiro.
    try:
        usuario_id = int(usuario_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido."
        )

    # Confere se o usuário do token ainda existe no banco.
    usuario = buscar_usuario(usuario_id)

    if usuario is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário não encontrado."
        )

    # Usuários inativos continuam cadastrados, mas não podem usar a API.
    if not usuario.ativo:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuário inativo."
        )

    return usuario


def obter_administrador_atual(
    usuario: Usuario = Depends(obter_usuario_atual)
) -> Usuario:
    """Permite continuar a requisição somente quando o usuário é administrador."""
    # Essa função é usada como dependência nas rotas administrativas.
    if usuario.perfil != "administrador":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Esta operação exige perfil de administrador."
        )

    return usuario