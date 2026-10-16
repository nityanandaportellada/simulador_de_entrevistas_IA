"""
routers/entrevistas.py

Endpoints relacionados às entrevistas
do Simulador de Entrevistas.

Responsabilidades:

- iniciar entrevista;
- receber área e subárea em entrevistas técnicas;
- consultar entrevista;
- listar as perguntas congeladas da entrevista;
- registrar respostas;
- consultar respostas;
- finalizar entrevista.

O usuário da entrevista é determinado
pelo token JWT.

Para entrevistas técnicas, o frontend informa:

- area_tecnica_id;
- subarea_tecnica_id.

O backend valida os vínculos e congela as perguntas
no momento da criação da entrevista.
"""

from typing import Optional


from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status
)


from pydantic import (
    BaseModel,
    ConfigDict,
    Field
)


from ..models import Usuario


from ..schemas import RespostaCriar


from ..security import (
    obter_usuario_atual
)


from ..entrevistas import (
    criar_entrevista,
    buscar_entrevista,
    finalizar_entrevista,
    listar_perguntas_entrevista,
    contar_perguntas_entrevista
)


from ..respostas import (
    salvar_resposta,
    listar_respostas_entrevista,
    contar_respostas_entrevista
)


# ============================================================
# SCHEMA - CRIAR ENTREVISTA
# ============================================================

class EntrevistaCriar(BaseModel):
    """
    Dados utilizados para iniciar uma entrevista.

    Para tipos que não utilizam área técnica:

        area_tecnica_id = null
        subarea_tecnica_id = null

    Para tipos que utilizam área técnica:

        area_tecnica_id = obrigatório
        subarea_tecnica_id = obrigatório

    A obrigatoriedade é validada pela camada
    de serviço em entrevistas.py.
    """

    model_config = ConfigDict(
        extra="forbid"
    )


    tipo_entrevista_id: int = Field(
        gt=0
    )


    area_tecnica_id: Optional[int] = Field(
        default=None,
        gt=0
    )


    subarea_tecnica_id: Optional[int] = Field(
        default=None,
        gt=0
    )


# ============================================================
# ROUTER
# ============================================================

router = APIRouter(

    prefix="/entrevistas",

    tags=[
        "Entrevistas"
    ]

)


# ============================================================
# FUNÇÃO INTERNA DE AUTORIZAÇÃO
# ============================================================

def _obter_entrevista_autorizada(
    entrevista_id: int,
    usuario: Usuario
):
    """
    Busca uma entrevista e verifica se o usuário
    possui autorização para acessá-la.

    Estudantes somente podem acessar suas próprias
    entrevistas.

    Administradores podem acessar qualquer entrevista.
    """

    entrevista = buscar_entrevista(
        entrevista_id
    )


    if entrevista is None:

        raise HTTPException(

            status_code=(
                status.HTTP_404_NOT_FOUND
            ),

            detail=(
                "Entrevista não encontrada."
            )

        )


    if (

        usuario.perfil
        != "administrador"

        and

        entrevista.usuario_id
        != usuario.id

    ):

        raise HTTPException(

            status_code=(
                status.HTTP_403_FORBIDDEN
            ),

            detail=(
                "Acesso não autorizado."
            )

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
    Inicia uma nova entrevista para o
    usuário autenticado.

    O usuario_id não é recebido do frontend.

    Ele é obtido diretamente através
    do token JWT.

    Para entrevistas técnicas, a requisição
    também deverá informar:

    - area_tecnica_id;
    - subarea_tecnica_id.

    Durante a criação, o backend congela
    todas as perguntas que farão parte
    daquela entrevista.
    """

    if usuario.id is None:

        raise HTTPException(

            status_code=(
                status.HTTP_401_UNAUTHORIZED
            ),

            detail=(
                "Usuário autenticado inválido."
            )

        )


    try:

        entrevista_id = criar_entrevista(

            usuario_id=usuario.id,

            tipo_entrevista_id=(
                dados.tipo_entrevista_id
            ),

            area_tecnica_id=(
                dados.area_tecnica_id
            ),

            subarea_tecnica_id=(
                dados.subarea_tecnica_id
            )

        )


        entrevista = buscar_entrevista(
            entrevista_id
        )


        if entrevista is None:

            raise HTTPException(

                status_code=(
                    status.HTTP_500_INTERNAL_SERVER_ERROR
                ),

                detail=(
                    "A entrevista foi criada, mas "
                    "não pôde ser recuperada."
                )

            )


        return entrevista


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

    Administradores podem consultar
    qualquer entrevista.
    """

    return _obter_entrevista_autorizada(

        entrevista_id,

        usuario

    )


# ============================================================
# LISTAR PERGUNTAS DA ENTREVISTA
# ============================================================

@router.get(
    "/{entrevista_id}/perguntas"
)
def perguntas(
    entrevista_id: int,
    usuario: Usuario = Depends(
        obter_usuario_atual
    )
):
    """
    Retorna exclusivamente as perguntas que
    foram congeladas para esta entrevista.

    IMPORTANTE:

    Este endpoint não consulta novamente
    o catálogo atual de perguntas.

    Portanto, alterações administrativas
    realizadas depois do início da entrevista
    não modificam o conjunto retornado.
    """

    _obter_entrevista_autorizada(

        entrevista_id,

        usuario

    )


    try:

        return listar_perguntas_entrevista(
            entrevista_id
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

    A pergunta somente será aceita se fizer
    parte do conjunto congelado da entrevista.
    """

    entrevista = _obter_entrevista_autorizada(

        entrevista_id,

        usuario

    )


    # --------------------------------------------------------
    # VERIFICAR STATUS
    # --------------------------------------------------------

    if (
        entrevista.status
        != "em_andamento"
    ):

        raise HTTPException(

            status_code=(
                status.HTTP_400_BAD_REQUEST
            ),

            detail=(

                "Não é possível responder uma "
                "entrevista que não está em andamento."

            )

        )


    # --------------------------------------------------------
    # SALVAR RESPOSTA
    # --------------------------------------------------------

    try:

        resposta_id = salvar_resposta(

            entrevista_id=(
                entrevista_id
            ),

            pergunta_id=(
                dados.pergunta_id
            ),

            texto_resposta=(
                dados.texto_resposta
            ),

            tempo_resposta=(
                dados.tempo_resposta
            )

        )


        return {

            "id":
                resposta_id,

            "entrevista_id":
                entrevista_id,

            "pergunta_id":
                dados.pergunta_id,

            "mensagem":
                "Resposta registrada com sucesso."

        }


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

    As respostas são ordenadas conforme
    a ordem histórica das perguntas congeladas.
    """

    _obter_entrevista_autorizada(

        entrevista_id,

        usuario

    )


    return listar_respostas_entrevista(
        entrevista_id
    )


# ============================================================
# CONSULTAR PROGRESSO DA ENTREVISTA
# ============================================================

@router.get(
    "/{entrevista_id}/progresso"
)
def progresso(
    entrevista_id: int,
    usuario: Usuario = Depends(
        obter_usuario_atual
    )
):
    """
    Retorna a quantidade de perguntas e respostas
    existentes na entrevista.

    Este endpoint não altera a regra atual de
    finalização.

    Ele apenas permite que o frontend saiba
    quantas perguntas já foram respondidas.
    """

    _obter_entrevista_autorizada(

        entrevista_id,

        usuario

    )


    quantidade_perguntas = (
        contar_perguntas_entrevista(
            entrevista_id
        )
    )


    quantidade_respostas = (
        contar_respostas_entrevista(
            entrevista_id
        )
    )


    return {

        "entrevista_id":
            entrevista_id,

        "quantidade_perguntas":
            quantidade_perguntas,

        "quantidade_respostas":
            quantidade_respostas,

        "quantidade_pendentes":
            max(
                0,
                (
                    quantidade_perguntas
                    - quantidade_respostas
                )
            ),

        "todas_respondidas":
            (
                quantidade_perguntas > 0

                and

                quantidade_respostas
                >= quantidade_perguntas
            )

    }


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

    A regra atual permanece:

    - a entrevista precisa estar em andamento;
    - deve existir pelo menos uma resposta.

    A análise por IA continua sendo executada
    posteriormente pelo endpoint de análise.
    """

    entrevista = _obter_entrevista_autorizada(

        entrevista_id,

        usuario

    )


    # --------------------------------------------------------
    # VERIFICAR STATUS
    # --------------------------------------------------------

    if (
        entrevista.status
        != "em_andamento"
    ):

        raise HTTPException(

            status_code=(
                status.HTTP_400_BAD_REQUEST
            ),

            detail=(
                "A entrevista não está em andamento."
            )

        )


    # --------------------------------------------------------
    # VERIFICAR SE HÁ PERGUNTAS
    # --------------------------------------------------------

    quantidade_perguntas = (
        contar_perguntas_entrevista(
            entrevista_id
        )
    )


    if quantidade_perguntas <= 0:

        raise HTTPException(

            status_code=(
                status.HTTP_400_BAD_REQUEST
            ),

            detail=(

                "A entrevista não possui perguntas "
                "congeladas e não pode ser finalizada."

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

            status_code=(
                status.HTTP_400_BAD_REQUEST
            ),

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

                status_code=(
                    status.HTTP_400_BAD_REQUEST
                ),

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


        if entrevista_finalizada is None:

            raise HTTPException(

                status_code=(
                    status.HTTP_500_INTERNAL_SERVER_ERROR
                ),

                detail=(

                    "A entrevista foi finalizada, "
                    "mas não pôde ser recuperada."

                )

            )


        return {

            "entrevista_id":
                entrevista_id,

            "status":
                entrevista_finalizada.status,

            "data_fim":
                entrevista_finalizada.data_fim,

            "quantidade_perguntas":
                quantidade_perguntas,

            "quantidade_respostas":
                len(
                    respostas_registradas
                ),

            "mensagem":
                "Entrevista finalizada com sucesso."

        }


    except ValueError as erro:

        raise HTTPException(

            status_code=(
                status.HTTP_400_BAD_REQUEST
            ),

            detail=str(
                erro
            )

        )