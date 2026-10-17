"""Rotas usadas para consultar e administrar as áreas técnicas."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from ..areas_tecnicas import (
    ativar_area_tecnica,
    buscar_area_tecnica,
    cadastrar_area_tecnica,
    editar_area_tecnica,
    inativar_area_tecnica,
    listar_areas_tecnicas
)
from ..models import AreaTecnica, Usuario
from ..security import obter_administrador_atual, obter_usuario_atual
from ..subareas_tecnicas import listar_subareas_tecnicas


class AreaTecnicaCriar(BaseModel):
    """Define os dados aceitos no cadastro de uma nova área técnica."""
    nome: str = Field(min_length=2, max_length=150)
    descricao: Optional[str] = Field(default=None, max_length=500)
    ordem: Optional[int] = Field(default=None, ge=0)


class AreaTecnicaAtualizar(BaseModel):
    """Define os dados aceitos na edição de uma área técnica."""
    nome: str = Field(min_length=2, max_length=150)
    descricao: Optional[str] = Field(default=None, max_length=500)
    ordem: Optional[int] = Field(default=None, ge=0)


# Agrupa todas as rotas relacionadas às áreas técnicas.
router = APIRouter(prefix="/areas-tecnicas", tags=["Áreas Técnicas"])


@router.get("")
def listar(
    somente_ativas: bool = Query(default=True),
    usuario: Usuario = Depends(obter_usuario_atual)
):
    """Lista as áreas técnicas e permite incluir registros inativos pelo parâmetro da rota."""
    return listar_areas_tecnicas(somente_ativas=somente_ativas)


@router.get("/{area_id}")
def consultar(area_id: int, usuario: Usuario = Depends(obter_usuario_atual)):
    """Consulta uma área técnica pelo ID informado."""
    area = buscar_area_tecnica(area_id)

    if area is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Área técnica não encontrada."
        )

    return area


@router.get("/{area_id}/subareas")
def listar_subareas(
    area_id: int,
    somente_ativas: bool = Query(default=True),
    usuario: Usuario = Depends(obter_usuario_atual)
):
    """Lista as subáreas que pertencem a uma determinada área técnica."""
    # Antes de listar, confirma que a área informada realmente existe.
    area = buscar_area_tecnica(area_id)

    if area is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Área técnica não encontrada."
        )

    return listar_subareas_tecnicas(
        area_tecnica_id=area_id,
        somente_ativas=somente_ativas
    )


@router.post("", status_code=status.HTTP_201_CREATED)
def cadastrar(
    dados: AreaTecnicaCriar,
    administrador: Usuario = Depends(obter_administrador_atual)
):
    """Cadastra uma área técnica e cria automaticamente sua subárea Geral."""
    try:
        # Monta o objeto esperado pela camada de serviço.
        area = AreaTecnica(
            nome=dados.nome,
            descricao=dados.descricao,
            ativo=True,
            ordem=dados.ordem
        )

        area_id = cadastrar_area_tecnica(area)
        area_criada = buscar_area_tecnica(area_id)

        if area_criada is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="A área foi cadastrada, mas não pôde ser recuperada."
            )

        return area_criada
    except ValueError as erro:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(erro)
        )


@router.put("/{area_id}")
def atualizar(
    area_id: int,
    dados: AreaTecnicaAtualizar,
    administrador: Usuario = Depends(obter_administrador_atual)
):
    """Atualiza os dados administrativos de uma área técnica existente."""
    area_atual = buscar_area_tecnica(area_id)

    if area_atual is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Área técnica não encontrada."
        )

    try:
        # Mantém o status e a data de criação porque esta rota altera apenas os dados administrativos.
        area = AreaTecnica(
            id=area_id,
            nome=dados.nome,
            descricao=dados.descricao,
            ativo=area_atual.ativo,
            ordem=dados.ordem,
            data_criacao=area_atual.data_criacao
        )

        alterada = editar_area_tecnica(area_id, area)

        if not alterada:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Área técnica não encontrada."
            )

        return buscar_area_tecnica(area_id)
    except ValueError as erro:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(erro)
        )


@router.put("/{area_id}/inativar")
def inativar(
    area_id: int,
    administrador: Usuario = Depends(obter_administrador_atual)
):
    """Inativa uma área quando não existem perguntas ativas vinculadas a ela."""
    try:
        alterada = inativar_area_tecnica(area_id)

        if not alterada:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Área técnica não encontrada."
            )

        return buscar_area_tecnica(area_id)
    except ValueError as erro:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(erro)
        )


@router.put("/{area_id}/ativar")
def ativar(
    area_id: int,
    administrador: Usuario = Depends(obter_administrador_atual)
):
    """Reativa uma área técnica que estava inativa."""
    try:
        alterada = ativar_area_tecnica(area_id)

        if not alterada:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Área técnica não encontrada."
            )

        return buscar_area_tecnica(area_id)
    except ValueError as erro:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(erro)
        )