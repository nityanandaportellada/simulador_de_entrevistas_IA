
"""Rotas autenticadas de histórico, resumo e evolução das entrevistas."""

import logging
import sqlite3

from fastapi import APIRouter, Depends, HTTPException, status

from ..historico import (
    gerar_resumo_historico,
    listar_historico,
    obter_evolucao_criterios,
    obter_evolucao_pontuacoes
)
from ..models import Usuario
from ..security import obter_usuario_atual

router = APIRouter(prefix="/historico", tags=["Histórico"])
logger = logging.getLogger(__name__)


def _usuario_autorizado(usuario: Usuario) -> int:
    """Utiliza sempre o ID autenticado, nunca um ID recebido na URL."""
    if type(usuario.id) is not int or usuario.id <= 0:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciais inválidas.",
            headers={"WWW-Authenticate": "Bearer"}
        )
    return usuario.id


def _erro_historico(operacao: str, erro: Exception) -> HTTPException:
    """Registra somente o tipo da falha, sem expor notas ou detalhes internos."""
    logger.warning("Falha de integridade no histórico (%s): %s", operacao, type(erro).__name__)
    return HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail="O histórico possui dados inconsistentes e precisa de revisão."
    )


@router.get("")
def meu_historico(usuario: Usuario = Depends(obter_usuario_atual)):
    """Lista exclusivamente as entrevistas do usuário autenticado."""
    usuario_id = _usuario_autorizado(usuario)
    try:
        return listar_historico(usuario_id)
    except ValueError as erro:
        raise _erro_historico("listar", erro) from erro
    except sqlite3.Error as erro:
        logger.error("Falha de banco no histórico (listar): %s", type(erro).__name__)
        raise HTTPException(status_code=503, detail="Histórico indisponível no momento.") from erro


@router.get("/resumo")
def resumo_historico(usuario: Usuario = Depends(obter_usuario_atual)):
    """Resume as entrevistas sem divulgar notas ainda não publicadas."""
    usuario_id = _usuario_autorizado(usuario)
    try:
        return gerar_resumo_historico(usuario_id)
    except ValueError as erro:
        raise _erro_historico("resumo", erro) from erro
    except sqlite3.Error as erro:
        logger.error("Falha de banco no histórico (resumo): %s", type(erro).__name__)
        raise HTTPException(status_code=503, detail="Histórico indisponível no momento.") from erro


@router.get("/evolucao")
def evolucao(usuario: Usuario = Depends(obter_usuario_atual)):
    """Lista somente as pontuações de entrevistas avaliadas do usuário."""
    usuario_id = _usuario_autorizado(usuario)
    try:
        return obter_evolucao_pontuacoes(usuario_id)
    except ValueError as erro:
        raise _erro_historico("evolucao", erro) from erro
    except sqlite3.Error as erro:
        logger.error("Falha de banco no histórico (evolucao): %s", type(erro).__name__)
        raise HTTPException(status_code=503, detail="Histórico indisponível no momento.") from erro


@router.get("/evolucao-criterios")
def evolucao_criterios(usuario: Usuario = Depends(obter_usuario_atual)):
    """Mostra a evolução dos critérios somente de avaliações completas."""
    usuario_id = _usuario_autorizado(usuario)
    try:
        return obter_evolucao_criterios(usuario_id)
    except ValueError as erro:
        raise _erro_historico("evolucao-criterios", erro) from erro
    except sqlite3.Error as erro:
        logger.error("Falha de banco no histórico (evolucao-criterios): %s", type(erro).__name__)
        raise HTTPException(status_code=503, detail="Histórico indisponível no momento.") from erro
