"""
routers/perguntas.py

Endpoints relacionados ao banco de perguntas
do Simulador de Entrevistas.

Responsabilidades:

- listar perguntas;
- consultar perguntas;
- cadastrar perguntas;
- atualizar perguntas;
- ativar perguntas;
- inativar perguntas;
- filtrar perguntas por tipo;
- filtrar perguntas por competência;
- filtrar perguntas por área;
- filtrar perguntas por subárea.

Perguntas técnicas possuem obrigatoriamente:

- área técnica;
- subárea técnica.

Operações administrativas são permitidas
somente para administradores.

Usuários estudantes somente recebem perguntas
que estejam efetivamente disponíveis para uso.
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
    ConfigDict,
    Field
)


from ..models import (
    Usuario,
    Pergunta
)


from ..security import (
    obter_usuario_atual,
    obter_administrador_atual
)


from ..perguntas import (
    cadastrar_pergunta,
    buscar_pergunta,
    buscar_pergunta_ativa,
    listar_perguntas,
    editar_pergunta,
    desativar_pergunta,
    reativar_pergunta
)


# ============================================================
# SCHEMA - CRIAR PERGUNTA
# ============================================================

class PerguntaCriar(BaseModel):
    """
    Contrato utilizado para cadastrar perguntas.

    Para tipos que utilizam área técnica:

    area_tecnica_id
    e
    subarea_tecnica_id

    serão obrigatórios pela regra de negócio
    implementada em perguntas.py.
    """

    model_config = ConfigDict(
        extra="forbid"
    )


    tipo_entrevista_id: int = Field(
        gt=0
    )


    competencia_id: int = Field(
        gt=0
    )


    texto: str = Field(
        min_length=3,
        max_length=4000
    )


    exemplo_esperado: Optional[str] = Field(
        default=None,
        max_length=8000
    )


    ordem: Optional[int] = Field(
        default=None,
        gt=0
    )


    peso: float = Field(
        default=1.0,
        gt=0
    )


    usa_star: bool = False


    area_tecnica_id: Optional[int] = Field(
        default=None,
        gt=0
    )


    subarea_tecnica_id: Optional[int] = Field(
        default=None,
        gt=0
    )


# ============================================================
# SCHEMA - ATUALIZAR PERGUNTA
# ============================================================

class PerguntaAtualizar(BaseModel):
    """
    Contrato utilizado para atualização
    de uma pergunta.
    """

    model_config = ConfigDict(
        extra="forbid"
    )


    tipo_entrevista_id: int = Field(
        gt=0
    )


    competencia_id: int = Field(
        gt=0
    )


    texto: str = Field(
        min_length=3,
        max_length=4000
    )


    exemplo_esperado: Optional[str] = Field(
        default=None,
        max_length=8000
    )


    ordem: Optional[int] = Field(
        default=None,
        gt=0
    )


    peso: float = Field(
        default=1.0,
        gt=0
    )


    usa_star: bool = False


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

    prefix="/perguntas",

    tags=[
        "Perguntas"
    ]

)


# ============================================================
# LISTAR PERGUNTAS
# ============================================================

@router.get(
    ""
)
def listar(
    somente_ativas: bool = Query(
        default=True
    ),
    tipo_entrevista_id: Optional[int] = Query(
        default=None,
        gt=0
    ),
    competencia_id: Optional[int] = Query(
        default=None,
        gt=0
    ),
    area_tecnica_id: Optional[int] = Query(
        default=None,
        gt=0
    ),
    subarea_tecnica_id: Optional[int] = Query(
        default=None,
        gt=0
    ),
    usuario: Usuario = Depends(
        obter_usuario_atual
    )
):
    """
    Lista perguntas cadastradas.

    Administradores podem consultar registros
    ativos e inativos.

    Estudantes recebem somente perguntas
    disponíveis para utilização.

    Filtros disponíveis:

    - tipo_entrevista_id;
    - competencia_id;
    - area_tecnica_id;
    - subarea_tecnica_id;
    - somente_ativas.
    """

    # --------------------------------------------------------
    # ESTUDANTE NÃO PODE CONSULTAR INATIVAS
    # --------------------------------------------------------

    if usuario.perfil != "administrador":

        somente_ativas = True


    try:

        return listar_perguntas(

            somente_ativas=(
                somente_ativas
            ),

            tipo_entrevista_id=(
                tipo_entrevista_id
            ),

            competencia_id=(
                competencia_id
            ),

            area_tecnica_id=(
                area_tecnica_id
            ),

            subarea_tecnica_id=(
                subarea_tecnica_id
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

    Administradores podem consultar inclusive
    perguntas inativas.

    Estudantes somente podem consultar perguntas
    efetivamente disponíveis para utilização.
    """

    try:

        if usuario.perfil == "administrador":

            pergunta = buscar_pergunta(
                pergunta_id
            )


        else:

            pergunta = buscar_pergunta_ativa(
                pergunta_id
            )


        if pergunta is None:

            raise HTTPException(

                status_code=(
                    status.HTTP_404_NOT_FOUND
                ),

                detail=(
                    "Pergunta não encontrada."
                )

            )


        return pergunta


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

    Regras:

    Para tipo sem área técnica:

        area_tecnica_id = null
        subarea_tecnica_id = null

    Para tipo com área técnica:

        area_tecnica_id = obrigatório
        subarea_tecnica_id = obrigatório
    """

    try:

        pergunta = Pergunta(

            tipo_entrevista_id=(
                dados.tipo_entrevista_id
            ),

            competencia_id=(
                dados.competencia_id
            ),

            texto=(
                dados.texto
            ),

            exemplo_esperado=(
                dados.exemplo_esperado
            ),

            ordem=(
                dados.ordem
            ),

            ativa=True,

            peso=(
                dados.peso
            ),

            usa_star=(
                dados.usa_star
            ),

            area_tecnica_id=(
                dados.area_tecnica_id
            ),

            subarea_tecnica_id=(
                dados.subarea_tecnica_id
            )

        )


        pergunta_id = cadastrar_pergunta(
            pergunta
        )


        pergunta_criada = buscar_pergunta(
            pergunta_id
        )


        if pergunta_criada is None:

            raise HTTPException(

                status_code=(
                    status.HTTP_500_INTERNAL_SERVER_ERROR
                ),

                detail=(
                    "A pergunta foi cadastrada, "
                    "mas não pôde ser recuperada."
                )

            )


        return pergunta_criada


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

    O status ativo/inativo atual é preservado.

    Caso a pergunta passe de um tipo não técnico
    para técnico, área e subárea tornam-se
    obrigatórias.

    Caso passe de um tipo técnico para um tipo
    que não utiliza área, área e subárea devem
    ser enviadas como null.
    """

    try:

        pergunta_atual = buscar_pergunta(
            pergunta_id
        )


        if pergunta_atual is None:

            raise HTTPException(

                status_code=(
                    status.HTTP_404_NOT_FOUND
                ),

                detail=(
                    "Pergunta não encontrada."
                )

            )


        pergunta = Pergunta(

            id=(
                pergunta_id
            ),

            tipo_entrevista_id=(
                dados.tipo_entrevista_id
            ),

            competencia_id=(
                dados.competencia_id
            ),

            texto=(
                dados.texto
            ),

            exemplo_esperado=(
                dados.exemplo_esperado
            ),

            ordem=(
                dados.ordem
            ),

            # ------------------------------------------------
            # PRESERVAR STATUS
            # ------------------------------------------------

            ativa=(
                pergunta_atual.ativa
            ),

            peso=(
                dados.peso
            ),

            usa_star=(
                dados.usa_star
            ),

            # ------------------------------------------------
            # ÁREA / SUBÁREA
            # ------------------------------------------------

            area_tecnica_id=(
                dados.area_tecnica_id
            ),

            subarea_tecnica_id=(
                dados.subarea_tecnica_id
            ),

            # ------------------------------------------------
            # PRESERVAR DATA
            # ------------------------------------------------

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

                status_code=(
                    status.HTTP_404_NOT_FOUND
                ),

                detail=(
                    "Pergunta não encontrada."
                )

            )


        return buscar_pergunta(
            pergunta_id
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

    O registro não é excluído,
    preservando o histórico.
    """

    try:

        pergunta = buscar_pergunta(
            pergunta_id
        )


        if pergunta is None:

            raise HTTPException(

                status_code=(
                    status.HTTP_404_NOT_FOUND
                ),

                detail=(
                    "Pergunta não encontrada."
                )

            )


        alterada = desativar_pergunta(
            pergunta_id
        )


        if not alterada:

            raise HTTPException(

                status_code=(
                    status.HTTP_400_BAD_REQUEST
                ),

                detail=(
                    "Não foi possível inativar "
                    "a pergunta."
                )

            )


        return buscar_pergunta(
            pergunta_id
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
    Reativa uma pergunta.

    Antes da reativação o backend verifica:

    - tipo de entrevista ativo;
    - competência ativa;
    - área ativa, quando aplicável;
    - subárea ativa, quando aplicável;
    - vínculo correto entre área e subárea.
    """

    try:

        pergunta = buscar_pergunta(
            pergunta_id
        )


        if pergunta is None:

            raise HTTPException(

                status_code=(
                    status.HTTP_404_NOT_FOUND
                ),

                detail=(
                    "Pergunta não encontrada."
                )

            )


        alterada = reativar_pergunta(
            pergunta_id
        )


        if not alterada:

            raise HTTPException(

                status_code=(
                    status.HTTP_400_BAD_REQUEST
                ),

                detail=(
                    "Não foi possível ativar "
                    "a pergunta."
                )

            )


        return buscar_pergunta(
            pergunta_id
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