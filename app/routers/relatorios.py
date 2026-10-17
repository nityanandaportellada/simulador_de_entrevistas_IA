"""Rotas responsáveis pela consulta dos relatórios das entrevistas."""

from fastapi import APIRouter, Depends, HTTPException, status

from ..models import Usuario
from ..relatorios import buscar_dados_entrevista, gerar_relatorio
from ..security import obter_usuario_atual

router = APIRouter(prefix="/relatorios", tags=["Relatórios"])


@router.get("/entrevistas/{entrevista_id}")
def relatorio_entrevista(
    entrevista_id: int,
    usuario: Usuario = Depends(obter_usuario_atual)
):
    """Retorna o relatório quando o usuário possui permissão para visualizar a entrevista."""
    try:
        entrevista = buscar_dados_entrevista(
            entrevista_id
        )
    except ValueError as erro:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(erro)
        )

    # Estudantes só podem consultar relatórios das próprias entrevistas.
    if usuario.perfil != "administrador" and entrevista.usuario_id != usuario.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você não possui permissão para visualizar este relatório."
        )

    try:
        return gerar_relatorio(
            entrevista_id
        )
    except ValueError as erro:
        # Inconsistências históricas são devolvidas ao cliente e não são escondidas.
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(erro)
        )