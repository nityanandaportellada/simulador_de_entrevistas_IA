"""
routers/relatorios.py

Endpoints relacionados aos relatórios
das entrevistas.

Versão: 0.3

Responsabilidades:

- disponibilizar o relatório completo;
- validar se a entrevista existe;
- garantir que o estudante somente visualize
  suas próprias entrevistas;
- permitir acesso administrativo.
"""

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status
)

from ..models import Usuario

from ..security import obter_usuario_atual

from ..relatorios import (
    buscar_dados_entrevista,
    gerar_relatorio
)


# ============================================================
# ROUTER
# ============================================================

router = APIRouter(
    prefix="/relatorios",
    tags=["Relatórios"]
)


# ============================================================
# RELATÓRIO DE UMA ENTREVISTA
# ============================================================

@router.get(
    "/entrevistas/{entrevista_id}"
)
def relatorio_entrevista(
    entrevista_id: int,
    usuario: Usuario = Depends(
        obter_usuario_atual
    )
):
    """
    Retorna o relatório completo
    de uma entrevista.

    Estudantes somente podem visualizar
    suas próprias entrevistas.

    Administradores podem consultar
    qualquer entrevista.
    """

    # --------------------------------------------------------
    # BUSCAR ENTREVISTA
    # --------------------------------------------------------

    try:

        entrevista = buscar_dados_entrevista(
            entrevista_id
        )

    except ValueError as erro:

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(erro)
        )


    # --------------------------------------------------------
    # AUTORIZAÇÃO
    # --------------------------------------------------------

    if (
        usuario.perfil != "administrador"
        and entrevista.usuario_id != usuario.id
    ):

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Você não possui permissão "
                "para visualizar este relatório."
            )
        )


    # --------------------------------------------------------
    # GERAR RELATÓRIO
    # --------------------------------------------------------

    try:

        return gerar_relatorio(
            entrevista_id
        )

    except ValueError as erro:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(erro)
        )