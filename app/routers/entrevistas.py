"""
routers/entrevistas.py

Endpoints relacionados às entrevistas
do Simulador de Entrevistas.

Versão: 0.2

Responsabilidades:

- iniciar entrevista;
- consultar entrevista;
- registrar respostas;
- consultar respostas;
- finalizar entrevista.

O usuário da entrevista é determinado
pelo token JWT.
"""

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status
)

from ..models import Usuario

from ..schemas import (
    EntrevistaCriar,
    RespostaCriar
)

from ..security import obter_usuario_atual

from ..entrevistas import (
    criar_entrevista,
    buscar_entrevista,
    finalizar_entrevista
)

from ..respostas import (
    salvar_resposta,
    listar_respostas_entrevista
)


# ============================================================
# ROUTER
# ============================================================

router = APIRouter(
    prefix="/entrevistas",
    tags=["Entrevistas"]
)


# ============================================================
# FUNÇÃO INTERNA DE AUTORIZAÇÃO
# ============================================================

def _obter_entrevista_autorizada(
    entrevista_id: int,
    usuario: Usuario
):
    """
    Busca a entrevista e verifica se o usuário
    possui autorização para acessá-la.

    Estudantes somente podem acessar suas
    próprias entrevistas.

    Administradores podem acessar qualquer
    entrevista.
    """

    entrevista = buscar_entrevista(
        entrevista_id
    )

    if entrevista is None:

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Entrevista não encontrada."
        )


    if (
        usuario.perfil != "administrador"
        and entrevista.usuario_id != usuario.id
    ):

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso não autorizado."
        )


    return entrevista


# ============================================================
# INICIAR ENTREVISTA
# ============================================================

@router.post(
    "",
    status_code=status.HTTP_201_CREATED
)
def iniciar(
    dados: EntrevistaCriar,
    usuario: Usuario = Depends(
        obter_usuario_atual
    )
):
    """
    Inicia uma nova entrevista para
    o usuário autenticado.

    O usuario_id não é recebido do frontend.

    Ele é obtido diretamente através
    do token JWT.
    """

    try:

        entrevista_id = criar_entrevista(
            usuario_id=usuario.id,
            tipo_entrevista_id=(
                dados.tipo_entrevista_id
            )
        )

        entrevista = buscar_entrevista(
            entrevista_id
        )

        return entrevista

    except ValueError as erro:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(erro)
        )


# ============================================================
# CONSULTAR ENTREVISTA
# ============================================================

@router.get(
    "/{entrevista_id}"
)
def consultar(
    entrevista_id: int,
    usuario: Usuario = Depends(
        obter_usuario_atual
    )
):
    """
    Consulta uma entrevista específica.

    O estudante somente pode consultar
    entrevistas pertencentes a ele.
    """

    return _obter_entrevista_autorizada(
        entrevista_id,
        usuario
    )


# ============================================================
# REGISTRAR RESPOSTA
# ============================================================

@router.post(
    "/{entrevista_id}/respostas",
    status_code=status.HTTP_201_CREATED
)
def responder(
    entrevista_id: int,
    dados: RespostaCriar,
    usuario: Usuario = Depends(
        obter_usuario_atual
    )
):
    """
    Registra uma resposta fornecida
    pelo estudante durante a entrevista.
    """

    entrevista = _obter_entrevista_autorizada(
        entrevista_id,
        usuario
    )


    # --------------------------------------------------------
    # VERIFICAR STATUS DA ENTREVISTA
    # --------------------------------------------------------

    if entrevista.status != "em_andamento":

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Não é possível responder "
                "uma entrevista que não está "
                "em andamento."
            )
        )


    # --------------------------------------------------------
    # SALVAR RESPOSTA
    # --------------------------------------------------------

    try:

        resposta_id = salvar_resposta(
            entrevista_id=entrevista_id,
            pergunta_id=dados.pergunta_id,
            texto_resposta=dados.texto_resposta,
            tempo_resposta=dados.tempo_resposta
        )

        return {
            "id": resposta_id,

            "entrevista_id":
                entrevista_id,

            "pergunta_id":
                dados.pergunta_id,

            "mensagem":
                "Resposta registrada com sucesso."
        }

    except ValueError as erro:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(erro)
        )


# ============================================================
# LISTAR RESPOSTAS DA ENTREVISTA
# ============================================================

@router.get(
    "/{entrevista_id}/respostas"
)
def respostas(
    entrevista_id: int,
    usuario: Usuario = Depends(
        obter_usuario_atual
    )
):
    """
    Retorna todas as respostas registradas
    em determinada entrevista.
    """

    _obter_entrevista_autorizada(
        entrevista_id,
        usuario
    )

    return listar_respostas_entrevista(
        entrevista_id
    )


# ============================================================
# FINALIZAR ENTREVISTA
# ============================================================

@router.post(
    "/{entrevista_id}/finalizar"
)
def finalizar(
    entrevista_id: int,
    usuario: Usuario = Depends(
        obter_usuario_atual
    )
):
    """
    Finaliza uma entrevista.

    Nesta versão a finalização ainda não
    executa automaticamente a análise
    através da OpenAI.

    A integração com IA será realizada
    na próxima etapa.
    """

    entrevista = _obter_entrevista_autorizada(
        entrevista_id,
        usuario
    )


    # --------------------------------------------------------
    # VERIFICAR STATUS
    # --------------------------------------------------------

    if entrevista.status != "em_andamento":

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "A entrevista não está "
                "em andamento."
            )
        )


    # --------------------------------------------------------
    # VERIFICAR RESPOSTAS
    # --------------------------------------------------------

    respostas_registradas = (
        listar_respostas_entrevista(
            entrevista_id
        )
    )


    if not respostas_registradas:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "A entrevista não pode ser "
                "finalizada sem respostas."
            )
        )


    # --------------------------------------------------------
    # FINALIZAR
    # --------------------------------------------------------

    try:

        resultado = finalizar_entrevista(
            entrevista_id
        )

        if not resultado:

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Não foi possível finalizar "
                    "a entrevista."
                )
            )


        entrevista_finalizada = (
            buscar_entrevista(
                entrevista_id
            )
        )


        return {
            "entrevista_id":
                entrevista_id,

            "status":
                entrevista_finalizada.status,

            "data_fim":
                entrevista_finalizada.data_fim,

            "mensagem":
                "Entrevista finalizada com sucesso."
        }

    except ValueError as erro:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(erro)
        )