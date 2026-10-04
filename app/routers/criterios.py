"""
routers/criterios.py

Endpoints administrativos relacionados aos
critérios de avaliação.

Versão: 0.1
"""

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status
)

from ..models import Usuario

from ..schemas import (
    CriterioCriar,
    CriterioAtualizar,
    CriterioResposta,
    CriterioDetalheResposta,
    ResumoPesosResposta
)

from ..security import (
    obter_usuario_atual,
    obter_administrador_atual
)

from ..criterios import (
    cadastrar_criterio,
    listar_criterios,
    buscar_criterio,
    editar_criterio,
    ativar_criterio,
    inativar_criterio,
    obter_detalhes_criterio,
    obter_resumo_pesos
)


# ============================================================
# ROUTER
# ============================================================

router = APIRouter(
    prefix="/criterios",
    tags=["Critérios de Avaliação"]
)


# ============================================================
# RESUMO DOS PESOS
# ============================================================

@router.get(
    "/resumo/pesos",
    response_model=ResumoPesosResposta
)
def resumo_pesos(
    administrador: Usuario = Depends(
        obter_administrador_atual
    )
):
    """
    Retorna a distribuição atual dos pesos.

    A rota é declarada antes de /{criterio_id}
    para evitar conflito de roteamento.
    """

    return obter_resumo_pesos()


# ============================================================
# LISTAR
# ============================================================

@router.get(
    "",
    response_model=list[CriterioResposta]
)
def listar(
    somente_ativos: bool = False,
    usuario: Usuario = Depends(
        obter_usuario_atual
    )
):
    """
    Lista os critérios de avaliação.
    """

    return listar_criterios(
        somente_ativos=somente_ativos
    )


# ============================================================
# CONSULTAR
# ============================================================

@router.get(
    "/{criterio_id}",
    response_model=CriterioResposta
)
def consultar(
    criterio_id: int,
    usuario: Usuario = Depends(
        obter_usuario_atual
    )
):
    """
    Consulta um critério pelo ID.
    """

    try:

        criterio = buscar_criterio(
            criterio_id
        )

    except ValueError as erro:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(erro)
        )


    if criterio is None:

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Critério não encontrado."
        )


    return criterio


# ============================================================
# DETALHES
# ============================================================

@router.get(
    "/{criterio_id}/detalhes",
    response_model=CriterioDetalheResposta
)
def detalhes(
    criterio_id: int,
    administrador: Usuario = Depends(
        obter_administrador_atual
    )
):
    """
    Retorna detalhes administrativos.
    """

    try:

        criterio = obter_detalhes_criterio(
            criterio_id
        )

    except ValueError as erro:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(erro)
        )


    if criterio is None:

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Critério não encontrado."
        )


    return criterio


# ============================================================
# CADASTRAR
# ============================================================

@router.post(
    "",
    response_model=CriterioResposta,
    status_code=status.HTTP_201_CREATED
)
def cadastrar(
    dados: CriterioCriar,
    administrador: Usuario = Depends(
        obter_administrador_atual
    )
):
    """
    Cadastra um novo critério.
    """

    try:

        criterio_id = cadastrar_criterio(
            nome=dados.nome,
            descricao=dados.descricao,
            peso=dados.peso,
            ordem=dados.ordem
        )


        criterio = buscar_criterio(
            criterio_id
        )


        if criterio is None:

            raise HTTPException(
                status_code=(
                    status.HTTP_500_INTERNAL_SERVER_ERROR
                ),
                detail=(
                    "O critério foi cadastrado, "
                    "mas não pôde ser recuperado."
                )
            )


        return criterio


    except ValueError as erro:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(erro)
        )


# ============================================================
# ATUALIZAR
# ============================================================

@router.put(
    "/{criterio_id}",
    response_model=CriterioResposta
)
def atualizar(
    criterio_id: int,
    dados: CriterioAtualizar,
    administrador: Usuario = Depends(
        obter_administrador_atual
    )
):
    """
    Atualiza nome, descrição, peso e ordem.
    """

    try:

        criterio_atual = buscar_criterio(
            criterio_id
        )


        if criterio_atual is None:

            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Critério não encontrado."
            )


        alterado = editar_criterio(
            criterio_id=criterio_id,
            nome=dados.nome,
            descricao=dados.descricao,
            peso=dados.peso,
            ordem=dados.ordem
        )


        if not alterado:

            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Critério não encontrado."
            )


        return buscar_criterio(
            criterio_id
        )


    except ValueError as erro:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(erro)
        )


# ============================================================
# INATIVAR
# ============================================================

@router.put(
    "/{criterio_id}/inativar",
    response_model=CriterioResposta
)
def inativar(
    criterio_id: int,
    administrador: Usuario = Depends(
        obter_administrador_atual
    )
):
    """
    Inativa um critério sem apagá-lo.
    """

    try:

        criterio = buscar_criterio(
            criterio_id
        )


        if criterio is None:

            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Critério não encontrado."
            )


        alterado = inativar_criterio(
            criterio_id
        )


        if not alterado:

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Não foi possível inativar "
                    "o critério."
                )
            )


        return buscar_criterio(
            criterio_id
        )


    except ValueError as erro:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(erro)
        )


# ============================================================
# ATIVAR
# ============================================================

@router.put(
    "/{criterio_id}/ativar",
    response_model=CriterioResposta
)
def ativar(
    criterio_id: int,
    administrador: Usuario = Depends(
        obter_administrador_atual
    )
):
    """
    Reativa um critério.
    """

    try:

        criterio = buscar_criterio(
            criterio_id
        )


        if criterio is None:

            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Critério não encontrado."
            )


        alterado = ativar_criterio(
            criterio_id
        )


        if not alterado:

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Não foi possível ativar "
                    "o critério."
                )
            )


        return buscar_criterio(
            criterio_id
        )


    except ValueError as erro:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(erro)
        )