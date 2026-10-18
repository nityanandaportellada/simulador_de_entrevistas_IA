
"""Rotas usadas para consultar e administrar as subáreas técnicas."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from pydantic import BaseModel, ConfigDict, Field

from ..areas_tecnicas import buscar_area_tecnica, listar_areas_tecnicas
from ..models import SubareaTecnica, Usuario
from ..security import obter_administrador_atual, obter_usuario_atual
from ..subareas_tecnicas import (
    ativar_subarea_tecnica,
    buscar_subarea_tecnica,
    cadastrar_subarea_tecnica,
    editar_subarea_tecnica,
    inativar_subarea_tecnica,
    listar_subareas_tecnicas
)


class SubareaTecnicaCriar(BaseModel):
    """Dados necessários para criar uma nova subárea."""
    model_config = ConfigDict(extra="forbid")

    area_tecnica_id: int = Field(gt=0)
    nome: str = Field(min_length=2, max_length=150)
    descricao: Optional[str] = Field(default=None, max_length=500)
    ordem: Optional[int] = Field(default=None, ge=0)


class SubareaTecnicaAtualizar(BaseModel):
    """Dados permitidos na edição de uma subárea. A área pai não pode ser alterada depois do cadastro."""
    model_config = ConfigDict(extra="forbid")

    nome: str = Field(min_length=2, max_length=150)
    descricao: Optional[str] = Field(default=None, max_length=500)
    ordem: Optional[int] = Field(default=None, ge=0)


# Agrupa as rotas de manutenção das subáreas técnicas.
router = APIRouter(prefix="/subareas-tecnicas", tags=["Subáreas Técnicas"])


@router.get("")
def listar(
    area_tecnica_id: Optional[int] = Query(default=None, gt=0),
    somente_ativas: bool = Query(default=True),
    usuario: Usuario = Depends(obter_usuario_atual)
):
    """Estudantes consultam só subáreas ativas de áreas também ativas."""
    try:
        if usuario.perfil != "administrador":
            somente_ativas = True
            if area_tecnica_id is not None:
                area = buscar_area_tecnica(area_tecnica_id)
                if area is None or not area.ativo:
                    raise HTTPException(status_code=404, detail="Área técnica não encontrada.")
        subareas = listar_subareas_tecnicas(
            area_tecnica_id=area_tecnica_id,
            somente_ativas=somente_ativas
        )
        if usuario.perfil == "administrador":
            return subareas
        # Mesmo uma subárea ativa fica invisível se a área pai foi inativada.
        areas_ativas = {area.id for area in listar_areas_tecnicas(somente_ativas=True)}
        return [subarea for subarea in subareas if subarea.area_tecnica_id in areas_ativas]
    except ValueError as erro:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(erro))


@router.get("/{subarea_id}")
def consultar(subarea_id: int = Path(gt=0), usuario: Usuario = Depends(obter_usuario_atual)):
    """Consulta uma subárea técnica pelo ID informado."""
    subarea = buscar_subarea_tecnica(subarea_id)

    if subarea is None:
        raise HTTPException(status_code=404, detail="Subárea técnica não encontrada.")
    if usuario.perfil != "administrador":
        area = buscar_area_tecnica(subarea.area_tecnica_id)
        if not subarea.ativo or area is None or not area.ativo:
            raise HTTPException(status_code=404, detail="Subárea técnica não encontrada.")
    return subarea


@router.post("", status_code=status.HTTP_201_CREATED)
def cadastrar(
    dados: SubareaTecnicaCriar,
    administrador: Usuario = Depends(obter_administrador_atual)
):
    """Cadastra uma nova subárea técnica em uma área existente."""
    try:
        # A subárea criada manualmente nunca é marcada como Geral.
        subarea = SubareaTecnica(
            area_tecnica_id=dados.area_tecnica_id,
            nome=dados.nome,
            descricao=dados.descricao,
            eh_geral=False,
            ativo=True,
            ordem=dados.ordem
        )

        subarea_id = cadastrar_subarea_tecnica(subarea)
        subarea_criada = buscar_subarea_tecnica(subarea_id)

        if subarea_criada is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="A subárea foi cadastrada, mas não pôde ser recuperada."
            )

        return subarea_criada
    except ValueError as erro:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(erro))


@router.put("/{subarea_id}")
def atualizar(
    subarea_id: int,
    dados: SubareaTecnicaAtualizar,
    administrador: Usuario = Depends(obter_administrador_atual)
):
    """Atualiza nome, descrição e ordem sem permitir a troca da área pai."""
    # Confirma a existência antes de tentar editar o registro.
    subarea_atual = buscar_subarea_tecnica(subarea_id)

    if subarea_atual is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subárea técnica não encontrada."
        )

    try:
        alterada = editar_subarea_tecnica(
            subarea_id=subarea_id,
            nome=dados.nome,
            descricao=dados.descricao,
            ordem=dados.ordem
        )

        if not alterada:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Subárea técnica não encontrada."
            )

        return buscar_subarea_tecnica(subarea_id)
    except ValueError as erro:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(erro))


@router.put("/{subarea_id}/inativar")
def inativar(
    subarea_id: int,
    administrador: Usuario = Depends(obter_administrador_atual)
):
    """Inativa uma subárea quando as regras de proteção permitem a operação."""
    try:
        # O serviço bloqueia a Geral e subáreas com perguntas ativas.
        alterada = inativar_subarea_tecnica(subarea_id)

        if not alterada:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Subárea técnica não encontrada."
            )

        return buscar_subarea_tecnica(subarea_id)
    except ValueError as erro:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(erro))


@router.put("/{subarea_id}/ativar")
def ativar(
    subarea_id: int,
    administrador: Usuario = Depends(obter_administrador_atual)
):
    """Ativa uma subárea quando a área pai também estiver ativa."""
    try:
        alterada = ativar_subarea_tecnica(subarea_id)

        if not alterada:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Subárea técnica não encontrada."
            )

        return buscar_subarea_tecnica(subarea_id)
    except ValueError as erro:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(erro))
