
"""Rotas protegidas de consulta aos relatórios de entrevistas avaliadas."""

import logging

from fastapi import APIRouter, Depends, HTTPException, status

from ..models import Usuario
from ..relatorios import buscar_dados_entrevista, gerar_relatorio
from ..security import obter_usuario_atual

router = APIRouter(prefix="/relatorios", tags=["Relatórios"])
logger = logging.getLogger(__name__)


@router.get("/entrevistas/{entrevista_id}")
def relatorio_entrevista(entrevista_id: int, usuario: Usuario = Depends(obter_usuario_atual)):
    """Entrega o relatório somente ao proprietário ou administrador, após avaliação."""
    if entrevista_id <= 0:
        raise HTTPException(status_code=404, detail="Entrevista não encontrada.")

    try:
        entrevista = buscar_dados_entrevista(entrevista_id)
    except ValueError as erro:
        raise HTTPException(status_code=404, detail="Entrevista não encontrada.") from erro

    # Usa o mesmo 404 para IDs inexistentes e entrevistas pertencentes a terceiros.
    if usuario.perfil != "administrador" and entrevista.usuario_id != usuario.id:
        raise HTTPException(status_code=404, detail="Entrevista não encontrada.")

    if entrevista.status != "avaliada":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="O relatório estará disponível após a conclusão da avaliação."
        )

    try:
        return gerar_relatorio(entrevista_id)
    except ValueError as erro:
        # Não expõe detalhes de inconsistências de banco ou de snapshots ao cliente.
        logger.warning("Relatório inconsistente para entrevista %s (%s)", entrevista_id, type(erro).__name__)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="O relatório apresenta inconsistência histórica e precisa de revisão."
        ) from erro
