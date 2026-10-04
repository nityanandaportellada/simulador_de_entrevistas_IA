"""
routers/historico.py

Endpoints relacionados ao histórico
de entrevistas do estudante.

Versão: 0.3

Responsabilidades:

- consultar histórico de entrevistas;
- consultar resumo do histórico;
- consultar evolução das pontuações;
- consultar evolução por critério.

Todos os endpoints utilizam o usuário
identificado pelo token JWT.
"""

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status
)

from ..models import Usuario

from ..security import obter_usuario_atual

from ..historico import (
    listar_historico,
    gerar_resumo_historico,
    obter_evolucao_pontuacoes,
    obter_evolucao_criterios
)


# ============================================================
# ROUTER
# ============================================================

router = APIRouter(
    prefix="/historico",
    tags=["Histórico"]
)


# ============================================================
# HISTÓRICO COMPLETO
# ============================================================

@router.get("")
def meu_historico(
    usuario: Usuario = Depends(
        obter_usuario_atual
    )
):
    """
    Retorna todas as entrevistas
    pertencentes ao usuário autenticado.
    """

    try:

        return listar_historico(
            usuario.id
        )

    except ValueError as erro:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(erro)
        )


# ============================================================
# RESUMO DO HISTÓRICO
# ============================================================

@router.get(
    "/resumo"
)
def resumo_historico(
    usuario: Usuario = Depends(
        obter_usuario_atual
    )
):
    """
    Retorna indicadores resumidos
    do histórico do estudante.
    """

    try:

        return gerar_resumo_historico(
            usuario.id
        )

    except ValueError as erro:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(erro)
        )


# ============================================================
# EVOLUÇÃO DAS PONTUAÇÕES
# ============================================================

@router.get(
    "/evolucao"
)
def evolucao(
    usuario: Usuario = Depends(
        obter_usuario_atual
    )
):
    """
    Retorna a evolução cronológica
    das pontuações do estudante.
    """

    try:

        return obter_evolucao_pontuacoes(
            usuario.id
        )

    except ValueError as erro:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(erro)
        )


# ============================================================
# EVOLUÇÃO POR CRITÉRIO
# ============================================================

@router.get(
    "/evolucao-criterios"
)
def evolucao_criterios(
    usuario: Usuario = Depends(
        obter_usuario_atual
    )
):
    """
    Retorna a evolução do estudante
    em cada critério de avaliação.
    """

    try:

        return obter_evolucao_criterios(
            usuario.id
        )

    except ValueError as erro:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(erro)
        )