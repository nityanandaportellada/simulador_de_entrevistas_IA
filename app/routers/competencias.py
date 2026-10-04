"""
routers/competencias.py

Endpoints relacionados às competências
do Simulador de Entrevistas.

Versão: 0.2

Responsabilidades:

- listar competências;
- consultar competências;
- consultar detalhes administrativos;
- cadastrar competências;
- atualizar competências;
- ativar competências;
- inativar competências.

Operações de manutenção são exclusivas
do administrador.
"""

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status
)

from ..models import Usuario

from ..schemas import (
    CompetenciaCriar,
    CompetenciaAtualizar,
    CompetenciaResposta,
    CompetenciaDetalheResposta
)

from ..security import (
    obter_usuario_atual,
    obter_administrador_atual
)

from ..competencias import (
    cadastrar_competencia,
    listar_competencias,
    buscar_competencia,
    editar_competencia,
    ativar_competencia,
    inativar_competencia,
    obter_detalhes_competencia
)


# ============================================================
# ROUTER
# ============================================================

router = APIRouter(
    prefix="/competencias",
    tags=["Competências"]
)


# ============================================================
# LISTAR COMPETÊNCIAS
# ============================================================

@router.get(
    "",
    response_model=list[CompetenciaResposta]
)
def listar(
    somente_ativas: bool = False,
    usuario: Usuario = Depends(
        obter_usuario_atual
    )
):
    """
    Lista as competências cadastradas.

    Usuários autenticados podem consultar
    as competências.

    O parâmetro somente_ativas permite retornar
    somente competências disponíveis.
    """

    return listar_competencias(
        somente_ativas=somente_ativas
    )


# ============================================================
# CONSULTAR COMPETÊNCIA
# ============================================================

@router.get(
    "/{competencia_id}",
    response_model=CompetenciaResposta
)
def consultar(
    competencia_id: int,
    usuario: Usuario = Depends(
        obter_usuario_atual
    )
):
    """
    Consulta uma competência pelo ID.
    """

    try:

        competencia = buscar_competencia(
            competencia_id
        )

    except ValueError as erro:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(erro)
        )


    if competencia is None:

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Competência não encontrada."
        )


    return competencia


# ============================================================
# DETALHES ADMINISTRATIVOS
# ============================================================

@router.get(
    "/{competencia_id}/detalhes",
    response_model=CompetenciaDetalheResposta
)
def consultar_detalhes(
    competencia_id: int,
    administrador: Usuario = Depends(
        obter_administrador_atual
    )
):
    """
    Retorna informações administrativas
    da competência.

    Inclui:

    - descrição;
    - quantidade total de perguntas;
    - quantidade de perguntas ativas;
    - informação sobre utilização.

    Operação exclusiva do administrador.
    """

    try:

        competencia = obter_detalhes_competencia(
            competencia_id
        )

    except ValueError as erro:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(erro)
        )


    if competencia is None:

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Competência não encontrada."
        )


    return competencia


# ============================================================
# CADASTRAR COMPETÊNCIA
# ============================================================

@router.post(
    "",
    response_model=CompetenciaResposta,
    status_code=status.HTTP_201_CREATED
)
def cadastrar(
    dados: CompetenciaCriar,
    administrador: Usuario = Depends(
        obter_administrador_atual
    )
):
    """
    Cadastra uma nova competência.

    Operação exclusiva do administrador.
    """

    try:

        competencia_id = cadastrar_competencia(
            nome=dados.nome,
            descricao=dados.descricao
        )


        competencia = buscar_competencia(
            competencia_id
        )


        if competencia is None:

            raise HTTPException(
                status_code=(
                    status.HTTP_500_INTERNAL_SERVER_ERROR
                ),
                detail=(
                    "A competência foi cadastrada, "
                    "mas não pôde ser recuperada."
                )
            )


        return competencia


    except ValueError as erro:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(erro)
        )


# ============================================================
# ATUALIZAR COMPETÊNCIA
# ============================================================

@router.put(
    "/{competencia_id}",
    response_model=CompetenciaResposta
)
def atualizar(
    competencia_id: int,
    dados: CompetenciaAtualizar,
    administrador: Usuario = Depends(
        obter_administrador_atual
    )
):
    """
    Atualiza o nome e a descrição
    de uma competência.

    O status ativo/inativo é preservado.

    Operação exclusiva do administrador.
    """

    try:

        competencia = buscar_competencia(
            competencia_id
        )


        if competencia is None:

            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Competência não encontrada."
            )


        alterada = editar_competencia(
            competencia_id=competencia_id,
            nome=dados.nome,
            descricao=dados.descricao
        )


        if not alterada:

            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Competência não encontrada."
            )


        competencia_atualizada = buscar_competencia(
            competencia_id
        )


        return competencia_atualizada


    except ValueError as erro:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(erro)
        )


# ============================================================
# INATIVAR COMPETÊNCIA
# ============================================================

@router.put(
    "/{competencia_id}/inativar",
    response_model=CompetenciaResposta
)
def inativar(
    competencia_id: int,
    administrador: Usuario = Depends(
        obter_administrador_atual
    )
):
    """
    Inativa uma competência.

    O registro permanece no banco,
    preservando o histórico.

    Operação exclusiva do administrador.
    """

    try:

        competencia = buscar_competencia(
            competencia_id
        )


        if competencia is None:

            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Competência não encontrada."
            )


        alterada = inativar_competencia(
            competencia_id
        )


        if not alterada:

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Não foi possível inativar "
                    "a competência."
                )
            )


        return buscar_competencia(
            competencia_id
        )


    except ValueError as erro:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(erro)
        )


# ============================================================
# ATIVAR COMPETÊNCIA
# ============================================================

@router.put(
    "/{competencia_id}/ativar",
    response_model=CompetenciaResposta
)
def ativar(
    competencia_id: int,
    administrador: Usuario = Depends(
        obter_administrador_atual
    )
):
    """
    Reativa uma competência anteriormente
    inativada.

    Operação exclusiva do administrador.
    """

    try:

        competencia = buscar_competencia(
            competencia_id
        )


        if competencia is None:

            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Competência não encontrada."
            )


        alterada = ativar_competencia(
            competencia_id
        )


        if not alterada:

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Não foi possível ativar "
                    "a competência."
                )
            )


        return buscar_competencia(
            competencia_id
        )


    except ValueError as erro:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(erro)
        )