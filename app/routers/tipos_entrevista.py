"""
routers/tipos_entrevista.py

Endpoints relacionados aos tipos de entrevista
do Simulador de Entrevistas.

Versão: 0.1

Responsabilidades:

- listar tipos de entrevista;
- consultar tipo de entrevista;
- consultar detalhes administrativos;
- cadastrar tipos de entrevista;
- atualizar tipos de entrevista;
- ativar tipos de entrevista;
- inativar tipos de entrevista.

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
    TipoEntrevistaCriar,
    TipoEntrevistaAtualizar,
    TipoEntrevistaResposta,
    TipoEntrevistaDetalheResposta
)

from ..security import (
    obter_usuario_atual,
    obter_administrador_atual
)

from ..tipos_entrevista import (
    cadastrar_tipo_entrevista,
    listar_tipos_entrevista,
    buscar_tipo_entrevista,
    editar_tipo_entrevista,
    ativar_tipo_entrevista,
    inativar_tipo_entrevista,
    obter_detalhes_tipo_entrevista
)


# ============================================================
# ROUTER
# ============================================================

router = APIRouter(
    prefix="/tipos-entrevista",
    tags=["Tipos de Entrevista"]
)


# ============================================================
# LISTAR TIPOS DE ENTREVISTA
# ============================================================

@router.get(
    "",
    response_model=list[TipoEntrevistaResposta]
)
def listar(
    somente_ativos: bool = False,
    usuario: Usuario = Depends(
        obter_usuario_atual
    )
):
    """
    Lista os tipos de entrevista cadastrados.

    Usuários autenticados podem consultar
    os tipos de entrevista.

    O parâmetro somente_ativos permite retornar
    apenas os tipos atualmente disponíveis.
    """

    return listar_tipos_entrevista(
        somente_ativos=somente_ativos
    )


# ============================================================
# CONSULTAR TIPO DE ENTREVISTA
# ============================================================

@router.get(
    "/{tipo_entrevista_id}",
    response_model=TipoEntrevistaResposta
)
def consultar(
    tipo_entrevista_id: int,
    usuario: Usuario = Depends(
        obter_usuario_atual
    )
):
    """
    Consulta um tipo de entrevista pelo ID.
    """

    try:

        tipo = buscar_tipo_entrevista(
            tipo_entrevista_id
        )

    except ValueError as erro:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(erro)
        )


    if tipo is None:

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                "Tipo de entrevista não encontrado."
            )
        )


    return tipo


# ============================================================
# DETALHES ADMINISTRATIVOS
# ============================================================

@router.get(
    "/{tipo_entrevista_id}/detalhes",
    response_model=TipoEntrevistaDetalheResposta
)
def consultar_detalhes(
    tipo_entrevista_id: int,
    administrador: Usuario = Depends(
        obter_administrador_atual
    )
):
    """
    Retorna informações administrativas sobre
    um tipo de entrevista.

    Inclui:

    - quantidade de perguntas;
    - quantidade de entrevistas;
    - informação sobre utilização.

    Operação exclusiva do administrador.
    """

    try:

        tipo = obter_detalhes_tipo_entrevista(
            tipo_entrevista_id
        )

    except ValueError as erro:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(erro)
        )


    if tipo is None:

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                "Tipo de entrevista não encontrado."
            )
        )


    return tipo


# ============================================================
# CADASTRAR TIPO DE ENTREVISTA
# ============================================================

@router.post(
    "",
    response_model=TipoEntrevistaResposta,
    status_code=status.HTTP_201_CREATED
)
def cadastrar(
    dados: TipoEntrevistaCriar,
    administrador: Usuario = Depends(
        obter_administrador_atual
    )
):
    """
    Cadastra um novo tipo de entrevista.

    Operação permitida somente para
    administradores.
    """

    try:

        tipo_entrevista_id = (
            cadastrar_tipo_entrevista(
                dados.nome
            )
        )


        tipo_criado = buscar_tipo_entrevista(
            tipo_entrevista_id
        )


        if tipo_criado is None:

            raise HTTPException(
                status_code=(
                    status.HTTP_500_INTERNAL_SERVER_ERROR
                ),
                detail=(
                    "O tipo de entrevista foi cadastrado, "
                    "mas não pôde ser recuperado."
                )
            )


        return tipo_criado


    except ValueError as erro:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(erro)
        )


# ============================================================
# ATUALIZAR TIPO DE ENTREVISTA
# ============================================================

@router.put(
    "/{tipo_entrevista_id}",
    response_model=TipoEntrevistaResposta
)
def atualizar(
    tipo_entrevista_id: int,
    dados: TipoEntrevistaAtualizar,
    administrador: Usuario = Depends(
        obter_administrador_atual
    )
):
    """
    Atualiza o nome de um tipo de entrevista.

    O status ativo/inativo é preservado.

    Operação permitida somente para
    administradores.
    """

    try:

        tipo_atual = buscar_tipo_entrevista(
            tipo_entrevista_id
        )


        if tipo_atual is None:

            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=(
                    "Tipo de entrevista não encontrado."
                )
            )


        alterado = editar_tipo_entrevista(
            tipo_entrevista_id,
            dados.nome
        )


        if not alterado:

            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=(
                    "Tipo de entrevista não encontrado."
                )
            )


        tipo_atualizado = buscar_tipo_entrevista(
            tipo_entrevista_id
        )


        return tipo_atualizado


    except ValueError as erro:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(erro)
        )


# ============================================================
# INATIVAR TIPO DE ENTREVISTA
# ============================================================

@router.put(
    "/{tipo_entrevista_id}/inativar",
    response_model=TipoEntrevistaResposta
)
def inativar(
    tipo_entrevista_id: int,
    administrador: Usuario = Depends(
        obter_administrador_atual
    )
):
    """
    Inativa um tipo de entrevista.

    O registro não é excluído.

    Perguntas e entrevistas históricas continuam
    relacionadas ao tipo normalmente.
    """

    try:

        tipo = buscar_tipo_entrevista(
            tipo_entrevista_id
        )


        if tipo is None:

            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=(
                    "Tipo de entrevista não encontrado."
                )
            )


        alterado = inativar_tipo_entrevista(
            tipo_entrevista_id
        )


        if not alterado:

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Não foi possível inativar "
                    "o tipo de entrevista."
                )
            )


        return buscar_tipo_entrevista(
            tipo_entrevista_id
        )


    except ValueError as erro:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(erro)
        )


# ============================================================
# ATIVAR TIPO DE ENTREVISTA
# ============================================================

@router.put(
    "/{tipo_entrevista_id}/ativar",
    response_model=TipoEntrevistaResposta
)
def ativar(
    tipo_entrevista_id: int,
    administrador: Usuario = Depends(
        obter_administrador_atual
    )
):
    """
    Reativa um tipo de entrevista anteriormente
    inativado.

    Operação exclusiva do administrador.
    """

    try:

        tipo = buscar_tipo_entrevista(
            tipo_entrevista_id
        )


        if tipo is None:

            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=(
                    "Tipo de entrevista não encontrado."
                )
            )


        alterado = ativar_tipo_entrevista(
            tipo_entrevista_id
        )


        if not alterado:

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Não foi possível ativar "
                    "o tipo de entrevista."
                )
            )


        return buscar_tipo_entrevista(
            tipo_entrevista_id
        )


    except ValueError as erro:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(erro)
        )