"""
routers/analise.py

Endpoints relacionados à análise das entrevistas
utilizando Inteligência Artificial.

Versão: 0.2

Responsabilidades:

- permitir que o estudante solicite a análise
  de uma entrevista finalizada;
- validar se a entrevista pertence ao usuário;
- permitir acesso administrativo;
- chamar a camada de análise;
- retornar o resultado da avaliação.

A comunicação direta com a OpenAI não ocorre
neste arquivo.

Toda a lógica de IA está centralizada
em app/analise.py.
"""

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status
)

from ..models import Usuario

from ..security import obter_usuario_atual

from ..analise import analisar_entrevista

from ..database import conectar_banco


# ============================================================
# ROUTER
# ============================================================

router = APIRouter(
    prefix="/analise",
    tags=["Análise"]
)


# ============================================================
# VERIFICAR ACESSO À ENTREVISTA
# ============================================================

def verificar_acesso_entrevista(
    entrevista_id: int,
    usuario: Usuario
):
    """
    Verifica se a entrevista existe e se o usuário
    possui permissão para solicitar sua análise.

    Administradores podem acessar qualquer entrevista.

    Estudantes somente podem acessar entrevistas
    pertencentes a eles.
    """

    conexao = conectar_banco()

    cursor = conexao.cursor()

    try:

        cursor.execute(
            """
            SELECT
                id,
                usuario_id,
                status

            FROM entrevistas

            WHERE id = ?
            """,
            (
                entrevista_id,
            )
        )

        entrevista = cursor.fetchone()

    finally:

        conexao.close()


    if entrevista is None:

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Entrevista não encontrada."
        )


    if usuario.perfil == "administrador":

        return entrevista


    if entrevista["usuario_id"] != usuario.id:

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Você não possui permissão para "
                "analisar esta entrevista."
            )
        )


    return entrevista


# ============================================================
# ANALISAR ENTREVISTA
# ============================================================

@router.post(
    "/entrevistas/{entrevista_id}"
)
def executar_analise_entrevista(
    entrevista_id: int,
    usuario: Usuario = Depends(
        obter_usuario_atual
    )
):
    """
    Solicita a análise completa de uma entrevista.

    A entrevista deve:

    - existir;
    - pertencer ao estudante autenticado,
      exceto quando o usuário for administrador;
    - estar finalizada ou possuir erro anterior
      de análise.
    """

    entrevista = verificar_acesso_entrevista(
        entrevista_id,
        usuario
    )


    if entrevista["status"] not in (
        "finalizada",
        "erro_analise"
    ):

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "A entrevista precisa estar finalizada "
                "antes da análise."
            )
        )


    try:

        return analisar_entrevista(
            entrevista_id
        )

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

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=(
                "Erro durante a análise da entrevista: "
                f"{str(erro)}"
            )
        )