"""Rotas responsáveis pelas consultas do histórico de entrevistas."""

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


@router.get("")
def meu_historico(usuario: Usuario = Depends(obter_usuario_atual)):
    """Retorna as entrevistas do usuário autenticado."""
    try:
        return listar_historico(usuario.id)
    except ValueError as erro:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(erro)
        )


@router.get("/resumo")
def resumo_historico(usuario: Usuario = Depends(obter_usuario_atual)):
    """Retorna os indicadores resumidos do histórico do usuário."""
    try:
        return gerar_resumo_historico(usuario.id)
    except ValueError as erro:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(erro)
        )


@router.get("/evolucao")
def evolucao(usuario: Usuario = Depends(obter_usuario_atual)):
    """Retorna a evolução cronológica das pontuações do usuário."""
    try:
        return obter_evolucao_pontuacoes(usuario.id)
    except ValueError as erro:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(erro)
        )


@router.get("/evolucao-criterios")
def evolucao_criterios(usuario: Usuario = Depends(obter_usuario_atual)):
    """Retorna a evolução do usuário em cada critério de avaliação."""
    try:
        return obter_evolucao_criterios(usuario.id)
    except ValueError as erro:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(erro)
        )