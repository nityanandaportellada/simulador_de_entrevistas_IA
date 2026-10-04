"""
routers/perguntas.py

Endpoints relacionados ao banco de perguntas
do Simulador de Entrevistas.

Versão: 0.3

Responsabilidades:

- listar perguntas;
- consultar perguntas;
- cadastrar perguntas;
- atualizar perguntas;
- ativar perguntas;
- inativar perguntas.

Operações de manutenção são exclusivas
do administrador.

Os erros de validação provenientes da camada
de serviço são convertidos para HTTP 400.
"""

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status
)


from ..models import (
    Usuario,
    Pergunta
)


from ..schemas import (
    PerguntaCriar,
    PerguntaAtualizar
)


from ..security import (
    obter_usuario_atual,
    obter_administrador_atual
)


from ..perguntas import (
    cadastrar_pergunta,
    buscar_pergunta,
    listar_perguntas,
    editar_pergunta,
    desativar_pergunta,
    reativar_pergunta
)


# ============================================================
# ROUTER
# ============================================================

router = APIRouter(
    prefix="/perguntas",
    tags=["Perguntas"]
)


# ============================================================
# LISTAR PERGUNTAS
# ============================================================

@router.get("")
def listar(
    usuario: Usuario = Depends(
        obter_usuario_atual
    )
):
    """
    Lista as perguntas disponíveis.

    Usuários autenticados podem consultar
    as perguntas cadastradas.
    """

    return listar_perguntas()


# ============================================================
# CONSULTAR PERGUNTA
# ============================================================

@router.get(
    "/{pergunta_id}"
)
def consultar(
    pergunta_id: int,
    usuario: Usuario = Depends(
        obter_usuario_atual
    )
):
    """
    Consulta uma pergunta pelo ID.
    """

    try:

        pergunta = buscar_pergunta(
            pergunta_id
        )


        if pergunta is None:

            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Pergunta não encontrada."
            )


        return pergunta


    except HTTPException:

        raise


    except ValueError as erro:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(erro)
        )


# ============================================================
# CADASTRAR PERGUNTA
# ============================================================

@router.post(
    "",
    status_code=status.HTTP_201_CREATED
)
def cadastrar(
    dados: PerguntaCriar,
    administrador: Usuario = Depends(
        obter_administrador_atual
    )
):
    """
    Cadastra uma nova pergunta.

    Operação permitida somente para
    administradores.
    """

    try:

        pergunta = Pergunta(

            tipo_entrevista_id=(
                dados.tipo_entrevista_id
            ),

            competencia_id=(
                dados.competencia_id
            ),

            texto=dados.texto,

            exemplo_esperado=(
                dados.exemplo_esperado
            ),

            ordem=dados.ordem,

            ativa=True,

            peso=dados.peso,

            usa_star=dados.usa_star

        )


        pergunta_id = cadastrar_pergunta(
            pergunta
        )


        pergunta_criada = buscar_pergunta(
            pergunta_id
        )


        return pergunta_criada


    except ValueError as erro:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(erro)
        )


# ============================================================
# ATUALIZAR PERGUNTA
# ============================================================

@router.put(
    "/{pergunta_id}"
)
def atualizar(
    pergunta_id: int,
    dados: PerguntaAtualizar,
    administrador: Usuario = Depends(
        obter_administrador_atual
    )
):
    """
    Atualiza uma pergunta existente.

    Operação permitida somente para
    administradores.
    """

    try:

        pergunta_atual = buscar_pergunta(
            pergunta_id
        )


        if pergunta_atual is None:

            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Pergunta não encontrada."
            )


        pergunta = Pergunta(

            id=pergunta_id,

            tipo_entrevista_id=(
                dados.tipo_entrevista_id
            ),

            competencia_id=(
                dados.competencia_id
            ),

            texto=dados.texto,

            exemplo_esperado=(
                dados.exemplo_esperado
            ),

            ordem=dados.ordem,

            # Preserva o status atual.
            ativa=pergunta_atual.ativa,

            peso=dados.peso,

            usa_star=dados.usa_star,

            # Preserva a data original.
            data_criacao=(
                pergunta_atual.data_criacao
            )

        )


        alterada = editar_pergunta(
            pergunta_id,
            pergunta
        )


        if not alterada:

            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Pergunta não encontrada."
            )


        return buscar_pergunta(
            pergunta_id
        )


    except HTTPException:

        raise


    except ValueError as erro:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(erro)
        )


# ============================================================
# INATIVAR PERGUNTA
# ============================================================

@router.put(
    "/{pergunta_id}/inativar"
)
def inativar(
    pergunta_id: int,
    administrador: Usuario = Depends(
        obter_administrador_atual
    )
):
    """
    Inativa uma pergunta.

    A pergunta não é excluída do banco,
    preservando o histórico.
    """

    try:

        pergunta = buscar_pergunta(
            pergunta_id
        )


        if pergunta is None:

            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Pergunta não encontrada."
            )


        alterada = desativar_pergunta(
            pergunta_id
        )


        if not alterada:

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Não foi possível inativar "
                    "a pergunta."
                )
            )


        return {
            "mensagem":
                "Pergunta inativada com sucesso."
        }


    except HTTPException:

        raise


    except ValueError as erro:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(erro)
        )


# ============================================================
# ATIVAR PERGUNTA
# ============================================================

@router.put(
    "/{pergunta_id}/ativar"
)
def ativar(
    pergunta_id: int,
    administrador: Usuario = Depends(
        obter_administrador_atual
    )
):
    """
    Reativa uma pergunta anteriormente inativada.

    O serviço também verifica se:

    - o tipo de entrevista está ativo;
    - a competência está ativa.

    Caso alguma regra não seja atendida,
    o ValueError é convertido para HTTP 400.
    """

    try:

        pergunta = buscar_pergunta(
            pergunta_id
        )


        if pergunta is None:

            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Pergunta não encontrada."
            )


        alterada = reativar_pergunta(
            pergunta_id
        )


        if not alterada:

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Não foi possível ativar "
                    "a pergunta."
                )
            )


        pergunta_ativada = buscar_pergunta(
            pergunta_id
        )


        return {
            "mensagem":
                "Pergunta ativada com sucesso.",

            "pergunta":
                pergunta_ativada
        }


    except HTTPException:

        raise


    except ValueError as erro:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(erro)
        )