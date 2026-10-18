
"""Rotas protegidas para avaliação das entrevistas pela inteligência artificial."""

import logging

from fastapi import APIRouter, Depends, HTTPException, status

from ..analise import analisar_entrevista
from ..database import conectar_banco
from ..models import Usuario
from ..security import obter_usuario_atual

router = APIRouter(prefix="/analise", tags=["Análise"])
logger = logging.getLogger(__name__)


def verificar_acesso_entrevista(entrevista_id: int, usuario: Usuario):
    """Confere a existência e a propriedade antes de permitir a análise."""
    if entrevista_id <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Identificador de entrevista inválido.")

    conexao = conectar_banco()
    try:
        entrevista = conexao.execute(
            "SELECT id, usuario_id, status FROM entrevistas WHERE id = ?", (entrevista_id,)
        ).fetchone()
    finally:
        conexao.close()

    if entrevista is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entrevista não encontrada.")
    if usuario.perfil != "administrador" and entrevista["usuario_id"] != usuario.id:
        # Não informa ao estudante se uma entrevista de terceiro existe.
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entrevista não encontrada.")
    return entrevista


@router.post("/entrevistas/{entrevista_id}")
def executar_analise_entrevista(entrevista_id: int, usuario: Usuario = Depends(obter_usuario_atual)):
    """Analisa entrevistas finalizadas e permite repetir análises que falharam."""
    entrevista = verificar_acesso_entrevista(entrevista_id, usuario)
    if entrevista["status"] not in ("finalizada", "erro_analise"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A entrevista precisa estar finalizada ou com erro de análise para iniciar a avaliação."
        )

    try:
        # O serviço controla o status em transação e impede análises simultâneas.
        return analisar_entrevista(entrevista_id)
    except ValueError as erro:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(erro)) from erro
    except RuntimeError as erro:
        logger.error("Serviço de análise indisponível para entrevista %s (%s)", entrevista_id, type(erro).__name__)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Serviço de análise indisponível no momento. Verifique as configurações do servidor."
        ) from erro
    except Exception as erro:
        # Nunca retorna mensagens da OpenAI, SQL ou dados de configuração ao cliente.
        logger.error("Falha inesperada na análise da entrevista %s (%s)", entrevista_id, type(erro).__name__)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Não foi possível concluir a análise. Tente novamente mais tarde."
        ) from erro
