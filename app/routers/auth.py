
"""Rotas públicas de cadastro, bootstrap do primeiro administrador e login."""

import math
import threading
import time
from fastapi import APIRouter, Header, HTTPException, Request, status

from ..auth import (
    AdministradorJaExisteError,
    autenticar_usuario,
    cadastrar_estudante,
    cadastrar_primeiro_administrador
)
from ..schemas import LoginRequest, TokenResponse, UsuarioCriar, UsuarioResposta
from ..security import criar_token_acesso
from ..usuarios import buscar_usuario

router = APIRouter(prefix="/auth", tags=["Autenticação"])

# Controle inicial por IP e por processo. Em produção, aplicar também no proxy/gateway.
_LIMITE = {"login": (15, 600), "cadastro": (8, 3600), "bootstrap": (5, 3600)}
_tentativas: dict[tuple[str, str], list[float]] = {}
_trava = threading.Lock()


def _limitar_requisicoes(request: Request, operacao: str) -> None:
    """Limita a frequência de tentativas por IP sem confiar em cabeçalhos X-Forwarded-For."""
    ip = request.client.host if request.client else "desconhecido"
    limite, janela = _LIMITE[operacao]
    chave = (operacao, ip)
    agora = time.monotonic()
    with _trava:
        # Remove entradas expiradas quando a lista cresce para evitar uso ilimitado de memória.
        if len(_tentativas) >= 10000:
            for antiga in list(_tentativas):
                if not _tentativas[antiga] or _tentativas[antiga][-1] <= agora - 3600:
                    del _tentativas[antiga]
            if len(_tentativas) >= 10000 and chave not in _tentativas:
                raise HTTPException(status_code=429, detail="Muitas requisições. Tente novamente mais tarde.")
        instantes = [momento for momento in _tentativas.get(chave, []) if momento > agora - janela]
        if len(instantes) >= limite:
            espera = max(1, math.ceil(janela - (agora - instantes[0])))
            _tentativas[chave] = instantes
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Muitas tentativas. Tente novamente mais tarde.",
                headers={"Retry-After": str(espera)}
            )
        instantes.append(agora)
        _tentativas[chave] = instantes


@router.post("/cadastro", response_model=UsuarioResposta, status_code=status.HTTP_201_CREATED)
def cadastro(dados: UsuarioCriar, request: Request):
    """Cria somente estudante e limita cadastros repetidos por origem."""
    _limitar_requisicoes(request, "cadastro")
    try:
        usuario_id = cadastrar_estudante(nome=dados.nome, email=str(dados.email), senha=dados.senha)
        usuario = buscar_usuario(usuario_id)
        if usuario is None:
            raise HTTPException(status_code=500, detail="Usuário criado, mas não foi possível recuperá-lo.")
        return usuario
    except HTTPException:
        raise
    except ValueError as erro:
        raise HTTPException(status_code=400, detail=str(erro)) from erro


@router.post("/bootstrap-admin", response_model=UsuarioResposta, status_code=status.HTTP_201_CREATED)
def bootstrap_admin(dados: UsuarioCriar, request: Request, x_bootstrap_token: str | None = Header(default=None, alias="X-Bootstrap-Token")):
    """Permite somente a primeira conta administrativa, exigindo token de bootstrap."""
    _limitar_requisicoes(request, "bootstrap")
    try:
        usuario_id = cadastrar_primeiro_administrador(
            nome=dados.nome, email=str(dados.email), senha=dados.senha, token_bootstrap=x_bootstrap_token
        )
        usuario = buscar_usuario(usuario_id)
        if usuario is None:
            raise HTTPException(status_code=500, detail="Administrador criado, mas não foi possível recuperá-lo.")
        return usuario
    except HTTPException:
        raise
    except AdministradorJaExisteError as erro:
        raise HTTPException(status_code=409, detail=str(erro)) from erro
    except PermissionError as erro:
        raise HTTPException(status_code=401, detail="Token de bootstrap inválido.") from erro
    except RuntimeError as erro:
        # Não revela o valor nem outros detalhes do segredo administrativo.
        raise HTTPException(status_code=503, detail="Configuração administrativa indisponível.") from erro
    except ValueError as erro:
        raise HTTPException(status_code=400, detail=str(erro)) from erro


@router.post("/login", response_model=TokenResponse)
def login(dados: LoginRequest, request: Request):
    """Valida credenciais e limita tentativas antes de consultar o banco."""
    _limitar_requisicoes(request, "login")
    usuario = autenticar_usuario(email=str(dados.email), senha=dados.senha)
    if usuario is None:
        raise HTTPException(status_code=401, detail="E-mail ou senha inválidos.")
    token = criar_token_acesso(usuario_id=usuario.id, perfil=usuario.perfil)
    return {"access_token": token, "token_type": "bearer"}
