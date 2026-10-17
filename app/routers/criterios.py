"""Rotas usadas para consultar e administrar os critérios de avaliação."""

from fastapi import APIRouter, Depends, HTTPException, status

from ..criterios import (
    ativar_criterio,
    buscar_criterio,
    cadastrar_criterio,
    editar_criterio,
    inativar_criterio,
    listar_criterios,
    obter_detalhes_criterio,
    obter_resumo_pesos
)
from ..models import Usuario
from ..schemas import CriterioAtualizar, CriterioCriar, CriterioDetalheResposta, CriterioResposta, ResumoPesosResposta
from ..security import obter_administrador_atual, obter_usuario_atual

# Agrupa as rotas relacionadas aos critérios de avaliação.
router = APIRouter(prefix="/criterios", tags=["Critérios de Avaliação"])


@router.get("/resumo/pesos", response_model=ResumoPesosResposta)
def resumo_pesos(administrador: Usuario = Depends(obter_administrador_atual)):
    """Mostra a distribuição atual dos pesos dos critérios ativos."""
    # Esta rota fica antes de /{criterio_id} para que "resumo" não seja interpretado como um ID.
    return obter_resumo_pesos()


@router.get("", response_model=list[CriterioResposta])
def listar(somente_ativos: bool = False, usuario: Usuario = Depends(obter_usuario_atual)):
    """Lista os critérios de avaliação para qualquer usuário autenticado."""
    return listar_criterios(somente_ativos=somente_ativos)


@router.get("/{criterio_id}", response_model=CriterioResposta)
def consultar(criterio_id: int, usuario: Usuario = Depends(obter_usuario_atual)):
    """Consulta um critério de avaliação pelo ID informado."""
    try:
        criterio = buscar_criterio(criterio_id)
    except ValueError as erro:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(erro))

    if criterio is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Critério não encontrado.")

    return criterio


@router.get("/{criterio_id}/detalhes", response_model=CriterioDetalheResposta)
def detalhes(criterio_id: int, administrador: Usuario = Depends(obter_administrador_atual)):
    """Mostra os dados administrativos e o uso histórico de um critério."""
    try:
        criterio = obter_detalhes_criterio(criterio_id)
    except ValueError as erro:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(erro))

    if criterio is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Critério não encontrado.")

    return criterio


@router.post("", response_model=CriterioResposta, status_code=status.HTTP_201_CREATED)
def cadastrar(dados: CriterioCriar, administrador: Usuario = Depends(obter_administrador_atual)):
    """Cadastra um novo critério de avaliação."""
    try:
        # Cria o critério com os dados validados pelo schema e pelo serviço.
        criterio_id = cadastrar_criterio(
            nome=dados.nome,
            descricao=dados.descricao,
            peso=dados.peso,
            ordem=dados.ordem
        )

        criterio = buscar_criterio(criterio_id)

        if criterio is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="O critério foi cadastrado, mas não pôde ser recuperado."
            )

        return criterio
    except HTTPException:
        raise
    except ValueError as erro:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(erro))


@router.put("/{criterio_id}", response_model=CriterioResposta)
def atualizar(
    criterio_id: int,
    dados: CriterioAtualizar,
    administrador: Usuario = Depends(obter_administrador_atual)
):
    """Atualiza o nome, a descrição, o peso e a ordem de um critério."""
    try:
        # Primeiro confirma que o critério existe.
        criterio_atual = buscar_criterio(criterio_id)

        if criterio_atual is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Critério não encontrado.")

        alterado = editar_criterio(
            criterio_id=criterio_id,
            nome=dados.nome,
            descricao=dados.descricao,
            peso=dados.peso,
            ordem=dados.ordem
        )

        if not alterado:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Critério não encontrado.")

        return buscar_criterio(criterio_id)
    except HTTPException:
        raise
    except ValueError as erro:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(erro))


@router.put("/{criterio_id}/inativar", response_model=CriterioResposta)
def inativar(criterio_id: int, administrador: Usuario = Depends(obter_administrador_atual)):
    """Inativa um critério sem apagar suas avaliações históricas."""
    try:
        criterio = buscar_criterio(criterio_id)

        if criterio is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Critério não encontrado.")

        alterado = inativar_criterio(criterio_id)

        if not alterado:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Não foi possível inativar o critério.")

        return buscar_criterio(criterio_id)
    except HTTPException:
        raise
    except ValueError as erro:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(erro))


@router.put("/{criterio_id}/ativar", response_model=CriterioResposta)
def ativar(criterio_id: int, administrador: Usuario = Depends(obter_administrador_atual)):
    """Reativa um critério que estava inativo."""
    try:
        criterio = buscar_criterio(criterio_id)

        if criterio is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Critério não encontrado.")

        alterado = ativar_criterio(criterio_id)

        if not alterado:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Não foi possível ativar o critério.")

        return buscar_criterio(criterio_id)
    except HTTPException:
        raise
    except ValueError as erro:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(erro))