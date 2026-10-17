"""Rotas responsáveis por solicitar a análise das entrevistas."""

from fastapi import APIRouter, Depends, HTTPException, status

from ..analise import analisar_entrevista
from ..database import conectar_banco
from ..models import Usuario
from ..security import obter_usuario_atual

router = APIRouter(prefix="/analise", tags=["Análise"])


def verificar_acesso_entrevista(entrevista_id: int, usuario: Usuario):
    """Confere se a entrevista existe e se o usuário pode solicitar sua análise."""
    conexao = conectar_banco()
    cursor = conexao.cursor()

    try:
        cursor.execute(
            """
            SELECT id, usuario_id, status
            FROM entrevistas
            WHERE id = ?
            """,
            (entrevista_id,)
        )
        entrevista = cursor.fetchone()
    finally:
        conexao.close()

    if entrevista is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Entrevista não encontrada."
        )

    # Administradores podem analisar qualquer entrevista.
    if usuario.perfil == "administrador":
        return entrevista

    # Estudantes só podem analisar entrevistas que pertencem a eles.
    if entrevista["usuario_id"] != usuario.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Você não possui permissão para analisar esta entrevista."
        )

    return entrevista


@router.post("/entrevistas/{entrevista_id}")
def executar_analise_entrevista(
    entrevista_id: int,
    usuario: Usuario = Depends(obter_usuario_atual)
):
    """Solicita a análise completa de uma entrevista finalizada ou com erro anterior de análise."""
    entrevista = verificar_acesso_entrevista(entrevista_id, usuario)

    if entrevista["status"] not in ("finalizada", "erro_analise"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A entrevista precisa estar finalizada antes da análise."
        )

    try:
        return analisar_entrevista(entrevista_id)
    except ValueError as erro:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(erro)
        )
    except RuntimeError as erro:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(erro)
        )
    except Exception as erro:
        # Erros inesperados são convertidos em erro interno sem esconder que a análise falhou.
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro durante a análise da entrevista: {str(erro)}"
        )