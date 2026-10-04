"""
security.py

Camada de segurança HTTP da API.

Versão: 0.1

Responsabilidades:

- gerar tokens JWT;
- validar tokens JWT;
- identificar o usuário autenticado;
- proteger endpoints;
- controlar acesso administrativo.

IMPORTANTE:

A chave JWT deve ficar em variável de ambiente.

Nunca colocar chaves reais diretamente
no código-fonte.
"""

import os

from datetime import (
    datetime,
    timedelta,
    timezone
)

import jwt

from fastapi import (
    Depends,
    HTTPException,
    status
)

from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer
)

try:

    from .usuarios import buscar_usuario
    from .models import Usuario

except ImportError:

    from usuarios import buscar_usuario
    from models import Usuario


# ============================================================
# CONFIGURAÇÕES
# ============================================================

JWT_SECRET = os.getenv(
    "JWT_SECRET"
)

JWT_ALGORITHM = "HS256"

TOKEN_EXPIRACAO_MINUTOS = 60


# ============================================================
# BEARER
# ============================================================

bearer_scheme = HTTPBearer()


# ============================================================
# VALIDAR CONFIGURAÇÃO
# ============================================================

def _obter_jwt_secret() -> str:
    """
    Recupera a chave JWT.

    A aplicação não deve funcionar com uma
    chave padrão insegura.
    """

    if not JWT_SECRET:

        raise RuntimeError(
            "A variável JWT_SECRET "
            "não foi configurada."
        )

    return JWT_SECRET


# ============================================================
# GERAR TOKEN
# ============================================================

def criar_token_acesso(
    usuario_id: int,
    perfil: str
) -> str:
    """
    Gera token JWT para usuário autenticado.
    """

    agora = datetime.now(
        timezone.utc
    )

    expiracao = agora + timedelta(
        minutes=TOKEN_EXPIRACAO_MINUTOS
    )

    payload = {

        "sub":
            str(usuario_id),

        "perfil":
            perfil,

        "iat":
            agora,

        "exp":
            expiracao
    }

    return jwt.encode(
        payload,
        _obter_jwt_secret(),
        algorithm=JWT_ALGORITHM
    )


# ============================================================
# DECODIFICAR TOKEN
# ============================================================

def decodificar_token(
    token: str
) -> dict:
    """
    Valida e decodifica token JWT.
    """

    try:

        return jwt.decode(
            token,
            _obter_jwt_secret(),
            algorithms=[
                JWT_ALGORITHM
            ]
        )

    except jwt.ExpiredSignatureError:

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expirado."
        )

    except jwt.InvalidTokenError:

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido."
        )


# ============================================================
# USUÁRIO ATUAL
# ============================================================

def obter_usuario_atual(
    credenciais: HTTPAuthorizationCredentials = Depends(
        bearer_scheme
    )
) -> Usuario:
    """
    Recupera o usuário correspondente
    ao token enviado pela requisição.
    """

    payload = decodificar_token(
        credenciais.credentials
    )

    usuario_id = payload.get(
        "sub"
    )

    if usuario_id is None:

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido."
        )

    try:

        usuario_id = int(
            usuario_id
        )

    except ValueError:

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido."
        )


    usuario = buscar_usuario(
        usuario_id
    )


    if usuario is None:

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário não encontrado."
        )


    if not usuario.ativo:

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuário inativo."
        )


    return usuario


# ============================================================
# EXIGIR ADMINISTRADOR
# ============================================================

def obter_administrador_atual(
    usuario: Usuario = Depends(
        obter_usuario_atual
    )
) -> Usuario:
    """
    Permite acesso somente para administradores.
    """

    if usuario.perfil != "administrador":

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Esta operação exige "
                "perfil de administrador."
            )
        )

    return usuario