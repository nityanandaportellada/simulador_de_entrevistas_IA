"""
routers/subareas_tecnicas.py

Endpoints relacionados às subáreas técnicas
do Simulador de Entrevistas.

Responsabilidades:

- listar subáreas;
- consultar subárea;
- cadastrar subárea;
- editar subárea;
- ativar subárea;
- inativar subárea.

Consultas podem ser realizadas por usuários autenticados.

Operações de manutenção são exclusivas
do administrador.
"""

from typing import Optional


from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    status
)


from pydantic import (
    BaseModel,
    Field
)


from ..models import (
    SubareaTecnica,
    Usuario
)


from ..security import (
    obter_administrador_atual,
    obter_usuario_atual
)


from ..subareas_tecnicas import (
    ativar_subarea_tecnica,
    buscar_subarea_tecnica,
    cadastrar_subarea_tecnica,
    editar_subarea_tecnica,
    inativar_subarea_tecnica,
    listar_subareas_tecnicas
)


# ============================================================
# SCHEMAS
# ============================================================

class SubareaTecnicaCriar(BaseModel):
    """
    Dados necessários para criar
    uma nova subárea.
    """

    area_tecnica_id: int = Field(
        gt=0
    )

    nome: str = Field(
        min_length=2,
        max_length=150
    )

    descricao: Optional[str] = Field(
        default=None,
        max_length=500
    )

    ordem: Optional[int] = Field(
        default=None,
        ge=0
    )


class SubareaTecnicaAtualizar(BaseModel):
    """
    Dados permitidos na edição
    de uma subárea.

    A área pai não pode ser alterada
    depois do cadastro.
    """

    nome: str = Field(
        min_length=2,
        max_length=150
    )

    descricao: Optional[str] = Field(
        default=None,
        max_length=500
    )

    ordem: Optional[int] = Field(
        default=None,
        ge=0
    )


# ============================================================
# ROUTER
# ============================================================

router = APIRouter(

    prefix="/subareas-tecnicas",

    tags=[
        "Subáreas Técnicas"
    ]

)


# ============================================================
# LISTAR SUBÁREAS
# ============================================================

@router.get(
    ""
)
def listar(
    area_tecnica_id: Optional[int] = Query(
        default=None,
        gt=0
    ),
    somente_ativas: bool = Query(
        default=True
    ),
    usuario: Usuario = Depends(
        obter_usuario_atual
    )
):
    """
    Lista subáreas técnicas.

    Pode ser filtrada pela área através de:

    ?area_tecnica_id=6

    Por padrão retorna somente registros ativos.
    """

    try:

        return listar_subareas_tecnicas(

            area_tecnica_id=(
                area_tecnica_id
            ),

            somente_ativas=(
                somente_ativas
            )

        )


    except ValueError as erro:

        raise HTTPException(

            status_code=(
                status.HTTP_400_BAD_REQUEST
            ),

            detail=str(
                erro
            )

        )


# ============================================================
# CONSULTAR SUBÁREA
# ============================================================

@router.get(
    "/{subarea_id}"
)
def consultar(
    subarea_id: int,
    usuario: Usuario = Depends(
        obter_usuario_atual
    )
):
    """
    Consulta uma subárea pelo ID.
    """

    subarea = buscar_subarea_tecnica(
        subarea_id
    )


    if subarea is None:

        raise HTTPException(

            status_code=(
                status.HTTP_404_NOT_FOUND
            ),

            detail=(
                "Subárea técnica não encontrada."
            )

        )


    return subarea


# ============================================================
# CADASTRAR SUBÁREA
# ============================================================

@router.post(
    "",
    status_code=status.HTTP_201_CREATED
)
def cadastrar(
    dados: SubareaTecnicaCriar,
    administrador: Usuario = Depends(
        obter_administrador_atual
    )
):
    """
    Cadastra uma nova subárea técnica.

    A subárea Geral não pode ser cadastrada
    manualmente.
    """

    try:

        subarea = SubareaTecnica(

            area_tecnica_id=(
                dados.area_tecnica_id
            ),

            nome=dados.nome,

            descricao=(
                dados.descricao
            ),

            eh_geral=False,

            ativo=True,

            ordem=dados.ordem

        )


        subarea_id = (
            cadastrar_subarea_tecnica(
                subarea
            )
        )


        subarea_criada = (
            buscar_subarea_tecnica(
                subarea_id
            )
        )


        if subarea_criada is None:

            raise HTTPException(

                status_code=(
                    status.HTTP_500_INTERNAL_SERVER_ERROR
                ),

                detail=(
                    "A subárea foi cadastrada, mas "
                    "não pôde ser recuperada."
                )

            )


        return subarea_criada


    except ValueError as erro:

        raise HTTPException(

            status_code=(
                status.HTTP_400_BAD_REQUEST
            ),

            detail=str(
                erro
            )

        )


# ============================================================
# EDITAR SUBÁREA
# ============================================================

@router.put(
    "/{subarea_id}"
)
def atualizar(
    subarea_id: int,
    dados: SubareaTecnicaAtualizar,
    administrador: Usuario = Depends(
        obter_administrador_atual
    )
):
    """
    Edita uma subárea.

    A área pai não pode ser modificada.

    A opção Geral também não pode
    ser editada.
    """

    subarea_atual = (
        buscar_subarea_tecnica(
            subarea_id
        )
    )


    if subarea_atual is None:

        raise HTTPException(

            status_code=(
                status.HTTP_404_NOT_FOUND
            ),

            detail=(
                "Subárea técnica não encontrada."
            )

        )


    try:

        alterada = (
            editar_subarea_tecnica(

                subarea_id=(
                    subarea_id
                ),

                nome=dados.nome,

                descricao=(
                    dados.descricao
                ),

                ordem=dados.ordem

            )
        )


        if not alterada:

            raise HTTPException(

                status_code=(
                    status.HTTP_404_NOT_FOUND
                ),

                detail=(
                    "Subárea técnica não encontrada."
                )

            )


        return buscar_subarea_tecnica(
            subarea_id
        )


    except ValueError as erro:

        raise HTTPException(

            status_code=(
                status.HTTP_400_BAD_REQUEST
            ),

            detail=str(
                erro
            )

        )


# ============================================================
# INATIVAR SUBÁREA
# ============================================================

@router.put(
    "/{subarea_id}/inativar"
)
def inativar(
    subarea_id: int,
    administrador: Usuario = Depends(
        obter_administrador_atual
    )
):
    """
    Inativa uma subárea.

    A opção Geral nunca pode ser inativada.

    Também não é possível inativar uma subárea
    que possua perguntas ativas.
    """

    try:

        alterada = (
            inativar_subarea_tecnica(
                subarea_id
            )
        )


        if not alterada:

            raise HTTPException(

                status_code=(
                    status.HTTP_404_NOT_FOUND
                ),

                detail=(
                    "Subárea técnica não encontrada."
                )

            )


        return buscar_subarea_tecnica(
            subarea_id
        )


    except ValueError as erro:

        raise HTTPException(

            status_code=(
                status.HTTP_400_BAD_REQUEST
            ),

            detail=str(
                erro
            )

        )


# ============================================================
# ATIVAR SUBÁREA
# ============================================================

@router.put(
    "/{subarea_id}/ativar"
)
def ativar(
    subarea_id: int,
    administrador: Usuario = Depends(
        obter_administrador_atual
    )
):
    """
    Ativa uma subárea.

    A área pai precisa estar ativa.
    """

    try:

        alterada = (
            ativar_subarea_tecnica(
                subarea_id
            )
        )


        if not alterada:

            raise HTTPException(

                status_code=(
                    status.HTTP_404_NOT_FOUND
                ),

                detail=(
                    "Subárea técnica não encontrada."
                )

            )


        return buscar_subarea_tecnica(
            subarea_id
        )


    except ValueError as erro:

        raise HTTPException(

            status_code=(
                status.HTTP_400_BAD_REQUEST
            ),

            detail=str(
                erro
            )

        )