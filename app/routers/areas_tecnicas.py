"""
routers/areas_tecnicas.py

Endpoints relacionados às áreas técnicas
do Simulador de Entrevistas.

Responsabilidades:

- listar áreas técnicas;
- consultar área;
- consultar subáreas da área;
- cadastrar área;
- editar área;
- ativar área;
- inativar área.

Consultas são permitidas para usuários autenticados.

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
    AreaTecnica,
    Usuario
)


from ..security import (
    obter_administrador_atual,
    obter_usuario_atual
)


from ..areas_tecnicas import (
    ativar_area_tecnica,
    buscar_area_tecnica,
    cadastrar_area_tecnica,
    editar_area_tecnica,
    inativar_area_tecnica,
    listar_areas_tecnicas
)


from ..subareas_tecnicas import (
    listar_subareas_tecnicas
)


# ============================================================
# SCHEMAS DE ENTRADA
# ============================================================

class AreaTecnicaCriar(BaseModel):
    """
    Dados necessários para cadastrar
    uma nova área técnica.
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


class AreaTecnicaAtualizar(BaseModel):
    """
    Dados permitidos na edição de uma área.
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

    prefix="/areas-tecnicas",

    tags=[
        "Áreas Técnicas"
    ]

)


# ============================================================
# LISTAR ÁREAS
# ============================================================

@router.get(
    ""
)
def listar(
    somente_ativas: bool = Query(
        default=True
    ),
    usuario: Usuario = Depends(
        obter_usuario_atual
    )
):
    """
    Lista as áreas técnicas.

    Para o estudante, o comportamento padrão
    retorna apenas registros ativos.

    O administrador poderá consultar também
    os registros inativos utilizando:

    ?somente_ativas=false
    """

    return listar_areas_tecnicas(
        somente_ativas=(
            somente_ativas
        )
    )


# ============================================================
# CONSULTAR ÁREA
# ============================================================

@router.get(
    "/{area_id}"
)
def consultar(
    area_id: int,
    usuario: Usuario = Depends(
        obter_usuario_atual
    )
):
    """
    Consulta uma área técnica pelo ID.
    """

    area = buscar_area_tecnica(
        area_id
    )


    if area is None:

        raise HTTPException(

            status_code=(
                status.HTTP_404_NOT_FOUND
            ),

            detail=(
                "Área técnica não encontrada."
            )

        )


    return area


# ============================================================
# LISTAR SUBÁREAS DA ÁREA
# ============================================================

@router.get(
    "/{area_id}/subareas"
)
def listar_subareas(
    area_id: int,
    somente_ativas: bool = Query(
        default=True
    ),
    usuario: Usuario = Depends(
        obter_usuario_atual
    )
):
    """
    Lista as subáreas pertencentes
    a determinada área técnica.
    """

    area = buscar_area_tecnica(
        area_id
    )


    if area is None:

        raise HTTPException(

            status_code=(
                status.HTTP_404_NOT_FOUND
            ),

            detail=(
                "Área técnica não encontrada."
            )

        )


    return listar_subareas_tecnicas(

        area_tecnica_id=area_id,

        somente_ativas=(
            somente_ativas
        )

    )


# ============================================================
# CADASTRAR ÁREA
# ============================================================

@router.post(
    "",
    status_code=status.HTTP_201_CREATED
)
def cadastrar(
    dados: AreaTecnicaCriar,
    administrador: Usuario = Depends(
        obter_administrador_atual
    )
):
    """
    Cadastra uma nova área técnica.

    A subárea Geral é criada
    automaticamente.
    """

    try:

        area = AreaTecnica(

            nome=dados.nome,

            descricao=(
                dados.descricao
            ),

            ativo=True,

            ordem=dados.ordem

        )


        area_id = cadastrar_area_tecnica(
            area
        )


        area_criada = buscar_area_tecnica(
            area_id
        )


        if area_criada is None:

            raise HTTPException(

                status_code=(
                    status.HTTP_500_INTERNAL_SERVER_ERROR
                ),

                detail=(
                    "A área foi cadastrada, mas "
                    "não pôde ser recuperada."
                )

            )


        return area_criada


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
# ATUALIZAR ÁREA
# ============================================================

@router.put(
    "/{area_id}"
)
def atualizar(
    area_id: int,
    dados: AreaTecnicaAtualizar,
    administrador: Usuario = Depends(
        obter_administrador_atual
    )
):
    """
    Atualiza uma área técnica.
    """

    area_atual = buscar_area_tecnica(
        area_id
    )


    if area_atual is None:

        raise HTTPException(

            status_code=(
                status.HTTP_404_NOT_FOUND
            ),

            detail=(
                "Área técnica não encontrada."
            )

        )


    try:

        area = AreaTecnica(

            id=area_id,

            nome=dados.nome,

            descricao=(
                dados.descricao
            ),

            ativo=(
                area_atual.ativo
            ),

            ordem=dados.ordem,

            data_criacao=(
                area_atual.data_criacao
            )

        )


        alterada = editar_area_tecnica(
            area_id,
            area
        )


        if not alterada:

            raise HTTPException(

                status_code=(
                    status.HTTP_404_NOT_FOUND
                ),

                detail=(
                    "Área técnica não encontrada."
                )

            )


        return buscar_area_tecnica(
            area_id
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
# INATIVAR ÁREA
# ============================================================

@router.put(
    "/{area_id}/inativar"
)
def inativar(
    area_id: int,
    administrador: Usuario = Depends(
        obter_administrador_atual
    )
):
    """
    Inativa uma área.

    A operação é bloqueada caso existam
    perguntas ativas vinculadas.
    """

    try:

        alterada = inativar_area_tecnica(
            area_id
        )


        if not alterada:

            raise HTTPException(

                status_code=(
                    status.HTTP_404_NOT_FOUND
                ),

                detail=(
                    "Área técnica não encontrada."
                )

            )


        return buscar_area_tecnica(
            area_id
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
# ATIVAR ÁREA
# ============================================================

@router.put(
    "/{area_id}/ativar"
)
def ativar(
    area_id: int,
    administrador: Usuario = Depends(
        obter_administrador_atual
    )
):
    """
    Reativa uma área anteriormente inativada.
    """

    try:

        alterada = ativar_area_tecnica(
            area_id
        )


        if not alterada:

            raise HTTPException(

                status_code=(
                    status.HTTP_404_NOT_FOUND
                ),

                detail=(
                    "Área técnica não encontrada."
                )

            )


        return buscar_area_tecnica(
            area_id
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